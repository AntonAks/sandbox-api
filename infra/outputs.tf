output "server_ip" {
  description = "Public IPv4 of the workshop server."
  value       = aws_instance.app.public_ip
}

output "ssh_command" {
  description = "Ready-to-run SSH command to the server."
  value       = "ssh ubuntu@${aws_instance.app.public_ip}"
}
