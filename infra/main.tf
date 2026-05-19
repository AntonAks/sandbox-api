terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd*/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

locals {
  github_owner            = split("/", var.github_repository)[0]
  github_repository_lower = lower(var.github_repository)
  compose_prod_content    = file("${path.module}/../deploy/docker-compose.prod.yml")
  nginx_content           = file("${path.module}/../deploy/nginx.conf")
}

resource "aws_key_pair" "admin" {
  key_name   = "workshop-admin"
  public_key = var.ssh_public_key
}

resource "aws_security_group" "app" {
  name        = "workshop-app"
  description = "HTTP from world, SSH from admin"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH (key auth only, open so GitHub Actions deploy job can SSH in)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.admin.key_name
  vpc_security_group_ids      = [aws_security_group.app.id]
  subnet_id                   = tolist(data.aws_subnets.default.ids)[0]
  associate_public_ip_address = true

  # Cloud-init runs only at first boot. Without this, changes to user_data are
  # applied "in place" (silent metadata update) but the running instance keeps
  # the original .env / packages / etc. Force replacement so cloud-init re-runs.
  user_data_replace_on_change = true

  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    github_repository           = local.github_repository_lower
    github_owner                = local.github_owner
    ghcr_token                  = var.ghcr_token
    postgres_password           = var.postgres_password
    app_env                     = var.app_env
    jwt_secret_key              = var.jwt_secret_key
    access_token_expire_minutes = var.access_token_expire_minutes
    demo_user_email             = var.demo_user_email
    demo_user_password          = var.demo_user_password
    compose_prod_content        = local.compose_prod_content
    nginx_content               = local.nginx_content
  })

  tags = {
    Name = "workshop-app"
  }
}
