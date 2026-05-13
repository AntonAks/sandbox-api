# Infra (OpenTofu / Terraform on AWS)

Provisions a single EC2 instance (Ubuntu 24.04, `t3.small`, `eu-central-1`, default VPC) with cloud-init that:

1. Installs Docker + Docker Compose plugin.
2. Adds the default `ubuntu` user to the `docker` group.
3. Writes `/opt/workshop/{docker-compose.prod.yml,nginx.conf,.env}` and `chown`s them to `ubuntu`.
4. Logs in to `ghcr.io` as root and copies the docker credentials to `ubuntu` so subsequent SSH-driven deploys can `docker compose pull` private images.
5. Pulls and starts the app stack (app + Postgres + nginx).

The repo's `deploy/docker-compose.prod.yml` and `deploy/nginx.conf` are the canonical sources — Terraform reads them via `file()` and embeds them into cloud-init's `write_files`.

State lives in S3 (`sandbox-api-tfstate-<aws_account_id>/sandbox-api/terraform.tfstate`) with OpenTofu's native S3-object locking (`use_lockfile = true` in `backend.tf`).

## How it's run

**This infra is driven entirely from CI** — there's no need for local AWS credentials or local OpenTofu. The workflow `.github/workflows/infra.yml` runs `tofu plan` / `apply` / `destroy` on a `workflow_dispatch` trigger.

Local runs are still possible (see `terraform.tfvars.example`) but not required and not the canonical path.

## One-time AWS setup

1. **Create an IAM user** (or reuse one) with programmatic access. Suggested managed policies for a temporary workshop sandbox:
   - `AmazonEC2FullAccess`
   - `AmazonS3FullAccess` (or scoped to `sandbox-api-tfstate-*`)
   - Permissions to create/read SSH key pairs and security groups (covered by EC2FullAccess)

   Generate an **access key ID + secret access key** for that user.

2. **Generate an SSH keypair** locally if you don't have one you want to reuse:

   ```sh
   ssh-keygen -t ed25519 -f ~/.ssh/sandbox-api -C "sandbox-api workshop"
   ```

3. **Create a GitHub PAT** with `read:packages` scope: https://github.com/settings/tokens

4. **Generate a strong Postgres password**:

   ```sh
   openssl rand -base64 24
   ```

## GitHub repo secrets

Add the following in **Settings → Secrets and variables → Actions** (all repository-level):

| Secret                     | Value                                                                    |
|----------------------------|--------------------------------------------------------------------------|
| `AWS_ACCESS_KEY_ID`        | IAM user access key ID                                                   |
| `AWS_SECRET_ACCESS_KEY`    | IAM user secret access key                                               |
| `TF_VAR_ADMIN_IP`          | Your public IP as CIDR (e.g. `203.0.113.5/32`) — used for SSH allow-list |
| `TF_VAR_SSH_PUBLIC_KEY`    | Contents of your **public** key (`cat ~/.ssh/sandbox-api.pub`)           |
| `TF_VAR_GHCR_TOKEN`        | The GitHub PAT with `read:packages` scope                                |
| `TF_VAR_POSTGRES_PASSWORD` | The generated strong password                                            |
| `SSH_PRIVATE_KEY`          | Contents of your **private** key (`cat ~/.ssh/sandbox-api`)              |

> Note on naming: GitHub secrets are uppercase by convention; the `infra.yml` workflow maps `TF_VAR_ADMIN_IP` → env `TF_VAR_admin_ip` (lowercase suffix is what OpenTofu expects to populate `var.admin_ip`).

`AWS_DEFAULT_REGION`, `instance_type`, `app_env`, and `github_repository` are set by the workflow itself — no secrets needed.

## First-time bringup (order matters)

cloud-init on the EC2 instance does `docker compose pull` of `ghcr.io/<owner>/sandbox-api:latest` immediately. The image only exists after `deploy.yml`'s `build-and-push` job has run at least once on `main`. So the very first time:

1. **Merge to `main`** — `deploy.yml` runs `ci` + `build-and-push` and publishes the first `:latest` image. The `deploy` step in this run **will fail** because no server exists yet — that's expected, just ignore it.
2. **Actions → Infra → Run workflow → `apply`** — provisions the server; cloud-init successfully pulls the just-published image.
3. **Actions → Deploy → Run workflow** — re-runs the full pipeline; this time `deploy` + `smoke-test` go green.

After that, every push to `main` deploys cleanly without manual steps.

## Day-to-day flow

### Provision the server

1. GitHub UI → **Actions** → **Infra** → **Run workflow** → select `apply` → Run.
2. Wait for the job to finish. The summary prints `server_ip` and `ssh_command`.
3. (Optional) SSH in and wait for cloud-init to finish before traffic hits it:

   ```sh
   ssh ubuntu@<server_ip> 'cloud-init status --wait'
   curl http://<server_ip>/health/ready
   ```

   Expected: `{"status":"ok","db":"ok"}` 200.

### Deploy app changes

Merge to `main` (or use **Actions** → **Deploy** → **Run workflow**). `deploy.yml` reads `server_ip` from the Terraform state itself — no manual `SSH_HOST` secret to keep in sync.

### Tear down

GitHub UI → **Actions** → **Infra** → **Run workflow** → select `destroy` → Run.

This removes the EC2 instance, security group, and key pair. The S3 state bucket stays (cheap, has versioned history). Delete it manually if you really want zero traces:

```sh
aws s3 rb s3://sandbox-api-tfstate-<aws_account_id> --force
```

## Local-only run (optional, not the canonical path)

If you want to run `tofu` from your machine instead of CI:

```sh
cp terraform.tfvars.example terraform.tfvars   # fill in real values; gitignored
aws sso login   # or `aws configure` — provide creds however you like
tofu init -backend-config="bucket=sandbox-api-tfstate-$(aws sts get-caller-identity --query Account --output text)"
tofu apply
```

Beware: if CI and your laptop apply concurrently, the S3 object lock prevents corruption but one of them will fail — coordinate with yourself.
