variable "hcloud_token" {
  type        = string
  sensitive   = true
  description = "Hetzner Cloud API token."
}

variable "admin_ip" {
  type        = string
  description = "Admin IP CIDR allowed for SSH (e.g. \"1.2.3.4/32\")."
}

variable "ssh_public_key_path" {
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
  description = "Path to local SSH public key uploaded to Hetzner."
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
