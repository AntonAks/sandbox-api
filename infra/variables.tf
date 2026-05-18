variable "aws_region" {
  type        = string
  default     = "eu-central-1"
  description = "AWS region for all resources."
}

variable "instance_type" {
  type        = string
  default     = "t3.small"
  description = "EC2 instance type."
}

variable "admin_ip" {
  type        = string
  description = "Admin IP CIDR allowed for SSH (e.g. \"1.2.3.4/32\")."
}

variable "ssh_public_key" {
  type        = string
  description = "OpenSSH public key contents (e.g. \"ssh-ed25519 AAAA... user@host\"). Uploaded to AWS as the EC2 key pair."
}

variable "github_repository" {
  type        = string
  description = "GitHub repo as \"owner/repo\". Lowercased for ghcr image path; original case used for owner login."
}

variable "ghcr_token" {
  type        = string
  sensitive   = true
  description = "GitHub PAT with read:packages scope, used by the server to docker login to ghcr.io."
}

variable "postgres_password" {
  type        = string
  sensitive   = true
  description = "Postgres superuser password for the production stack."
}

variable "app_env" {
  type        = string
  default     = "prod"
  description = "Value of ENV variable for the app (.env on server)."
}

variable "jwt_secret_key" {
  type        = string
  sensitive   = true
  description = "Secret used to sign JWT access tokens. Generate with `openssl rand -base64 48`."
}

variable "access_token_expire_minutes" {
  type        = number
  default     = 1440
  description = "JWT access token lifetime in minutes (default 24h)."
}
