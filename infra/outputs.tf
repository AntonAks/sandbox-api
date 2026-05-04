output "server_ip" {
  description = "Public IPv4 of the workshop server."
  value       = hcloud_server.app.ipv4_address
}

output "ssh_command" {
  description = "Ready-to-run SSH command to the server."
  value       = "ssh root@${hcloud_server.app.ipv4_address}"
}
