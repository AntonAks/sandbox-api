# Infra (OpenTofu / Terraform)

Provisions a single Hetzner Cloud server (cpx21 / fsn1, Ubuntu 24.04) with cloud-init that:

1. Installs Docker + Docker Compose plugin.
2. Writes `/opt/workshop/{docker-compose.prod.yml,nginx.conf,.env}`.
3. Logs in to `ghcr.io` with a read-only PAT.
4. Pulls and starts the app stack (app + Postgres + nginx).

The repo's `deploy/docker-compose.prod.yml` and `deploy/nginx.conf` are the canonical sources — Terraform reads them via `file()` and embeds them into cloud-init's `write_files`. Keep these in sync with what you want on the server.

## Setup

1. Create a Hetzner Cloud API token: https://docs.hetzner.com/cloud/api/getting-started/generating-api-token/
2. Create a GitHub PAT with `read:packages` scope (the server uses it to pull the private image): https://github.com/settings/tokens
3. Copy the example variables file and fill in real values:

   ```sh
   cp terraform.tfvars.example terraform.tfvars
   ```

   `terraform.tfvars` is gitignored — never commit it.
4. Init and apply:

   ```sh
   tofu init
   tofu apply
   ```

5. Wait for cloud-init to finish (the SSH session resolves before the stack is up):

   ```sh
   ssh root@$(tofu output -raw server_ip) 'cloud-init status --wait'
   ```

6. Verify the readiness probe:

   ```sh
   curl http://$(tofu output -raw server_ip)/health/ready
   ```

   Expected: `{"status":"ok","db":"ok"}` 200.

## After provisioning — wire CI/CD

Add the following secrets to the GitHub repo (Settings → Secrets and variables → Actions):

| Secret           | Value                                            |
|------------------|--------------------------------------------------|
| `SSH_HOST`       | `tofu output -raw server_ip`                     |
| `SSH_USER`       | `root`                                           |
| `SSH_PRIVATE_KEY`| Contents of the matching `~/.ssh/id_ed25519` (private key — the public key was uploaded to Hetzner via `ssh_public_key_path`) |

`GITHUB_TOKEN` is set by Actions automatically — no need to add it for `ghcr.io` push from the workflow.

## Tear down

```sh
tofu destroy
```

This removes the server, firewall, and SSH key resource. The Hetzner project itself stays — clean it up via the dashboard if needed.
