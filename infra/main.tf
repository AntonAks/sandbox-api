terraform {
  required_version = ">= 1.6"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.50"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

locals {
  github_owner            = split("/", var.github_repository)[0]
  github_repository_lower = lower(var.github_repository)
  compose_prod_content    = file("${path.module}/../deploy/docker-compose.prod.yml")
  nginx_content           = file("${path.module}/../deploy/nginx.conf")
}

resource "hcloud_ssh_key" "admin" {
  name       = "workshop-admin"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

resource "hcloud_firewall" "main" {
  name = "workshop-firewall"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = [var.admin_ip]
  }
}

resource "hcloud_server" "app" {
  name         = "workshop-app"
  image        = "ubuntu-24.04"
  server_type  = "cpx21"
  location     = "fsn1"
  ssh_keys     = [hcloud_ssh_key.admin.id]
  firewall_ids = [hcloud_firewall.main.id]

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    github_repository    = local.github_repository_lower
    github_owner         = local.github_owner
    ghcr_token           = var.ghcr_token
    postgres_password    = var.postgres_password
    app_env              = var.app_env
    compose_prod_content = local.compose_prod_content
    nginx_content        = local.nginx_content
  })
}
