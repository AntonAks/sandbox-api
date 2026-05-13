terraform {
  backend "s3" {
    # bucket name resolved at `tofu init` time via `-backend-config`
    # (see .github/workflows/infra.yml — bucket is sandbox-api-tfstate-<aws_account_id>)
    key          = "sandbox-api/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
