output "environment" {
  value = var.environment
}

output "app_public_ip" {
  description = "IP público fixo (Elastic IP) da VM da aplicação"
  value       = aws_eip.app.public_ip
}

output "app_private_ip" {
  value = aws_instance.app.private_ip
}

output "db_private_ip" {
  description = "Endereço privado usado pela API para acessar o MongoDB"
  value       = aws_instance.db.private_ip
}

output "db_public_ip" {
  description = "IP só de saída do banco (usado no teste de isolamento ACE-03)"
  value       = aws_instance.db.public_ip
}

output "app_domain" {
  description = "Nome DNS público gratuito (sslip.io) apontando para o Elastic IP"
  value       = "${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"
}

output "app_url" {
  value = "https://${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "mongo_volume_id" {
  value = aws_ebs_volume.mongo_data.id
}

output "backup_bucket" {
  value = var.backup_bucket_name
}

output "backup_prefix" {
  value = "${var.project}/${var.environment}"
}

output "inventory" {
  description = "Inventário de recursos (ACE-02)"
  value = {
    app = {
      name          = aws_instance.app.tags["Name"]
      id            = aws_instance.app.id
      instance_type = aws_instance.app.instance_type
      private_ip    = aws_instance.app.private_ip
      public_ip     = aws_eip.app.public_ip
    }
    db = {
      name          = aws_instance.db.tags["Name"]
      id            = aws_instance.db.id
      instance_type = aws_instance.db.instance_type
      private_ip    = aws_instance.db.private_ip
      data_volume   = aws_ebs_volume.mongo_data.id
    }
  }
}
