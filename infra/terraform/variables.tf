variable "project" {
  description = "Nome do projeto (prefixo dos recursos)"
  type        = string
  default     = "todo-app"
}

variable "environment" {
  description = "Ambiente de destino"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "homolog", "prod"], var.environment)
    error_message = "environment deve ser dev, homolog ou prod."
  }
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "instance_name" {
  description = "Nome base das VMs (recebem os sufixos -app e -db)"
  type        = string
  default     = "vm-pm04"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,40}$", var.instance_name))
    error_message = "instance_name deve ter de 3 a 40 caracteres: letras minúsculas, números e hífen."
  }
}

variable "instance_type" {
  description = "Tipo da VM da aplicação (Caddy + Nginx/React + API)"
  type        = string
  default     = "t3.micro"
}

variable "db_instance_type" {
  description = "Tipo da VM exclusiva do MongoDB"
  type        = string
  default     = "t3.micro"
}

variable "vpc_cidr" {
  description = "Faixa de endereços da VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "root_volume_size" {
  description = "Disco do sistema de cada VM (GiB)"
  type        = number
  default     = 10
}

variable "db_volume_size" {
  description = "Volume persistente de dados do MongoDB (GiB)"
  type        = number
  default     = 5
}

variable "admin_cidrs" {
  description = "Faixas autorizadas a administrar a VM da aplicação por SSH (ex.: IP fixo da equipe). A pipeline libera o próprio runner temporariamente."
  type        = list(string)
  default     = []
}

variable "ssh_public_key" {
  description = "Chave pública usada pelo Ansible (derivada do secret SSH_PRIVATE_KEY pela pipeline)"
  type        = string
}

variable "backup_bucket_name" {
  description = "Bucket S3 de backups (criado fora deste estado para sobreviver ao destroy)"
  type        = string
}
