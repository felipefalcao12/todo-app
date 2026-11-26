locals {
  name_prefix = "${var.project}-${var.environment}"
  az          = data.aws_availability_zones.available.names[0]
}

data "aws_availability_zones" "available" {
  state = "available"
}

# Ubuntu Server 24.04 LTS oficial (Canonical)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ---------------------------------------------------------------------------
# Rede
# ---------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name_prefix}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-igw" }
}

# Sub-rede da aplicação: única com entrada pública (HTTP/HTTPS)
resource "aws_subnet" "app" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 1)
  availability_zone       = local.az
  map_public_ip_on_launch = false

  tags = { Name = "${local.name_prefix}-subnet-app", Tier = "app" }
}

# Sub-rede do banco: nenhuma porta aberta para a internet. A saída para a
# internet (apt/imagens Docker/backup S3) usa um IP público só de saída —
# alternativa ao NAT Gateway, que custaria mais que todo o ambiente.
resource "aws_subnet" "db" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 2)
  availability_zone       = local.az
  map_public_ip_on_launch = false

  tags = { Name = "${local.name_prefix}-subnet-db", Tier = "db" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${local.name_prefix}-rt" }
}

resource "aws_route_table_association" "app" {
  subnet_id      = aws_subnet.app.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "db" {
  subnet_id      = aws_subnet.db.id
  route_table_id = aws_route_table.public.id
}

# ---------------------------------------------------------------------------
# Regras de acesso (Security Groups)
# Regras declaradas como recursos individuais: a regra SSH temporária que a
# pipeline cria para o runner não é apagada nem gera diferença no plano.
# ---------------------------------------------------------------------------
resource "aws_security_group" "app" {
  name        = "${local.name_prefix}-sg-app"
  description = "VM da aplicacao: HTTP/HTTPS publico, SSH restrito"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-app" }
}

resource "aws_vpc_security_group_ingress_rule" "app_http" {
  security_group_id = aws_security_group.app.id
  description       = "HTTP (redireciona para HTTPS e valida o certificado)"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "app_https" {
  security_group_id = aws_security_group.app.id
  description       = "HTTPS publico"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "app_ssh_admin" {
  for_each = toset(var.admin_cidrs)

  security_group_id = aws_security_group.app.id
  description       = "SSH administrativo"
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
}

resource "aws_vpc_security_group_egress_rule" "app_all" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "db" {
  name        = "${local.name_prefix}-sg-db"
  description = "VM do MongoDB: acesso somente a partir da VM da aplicacao"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-db" }
}

resource "aws_vpc_security_group_ingress_rule" "db_mongo_from_app" {
  security_group_id            = aws_security_group.db.id
  description                  = "MongoDB somente da API (VM da aplicacao)"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 27017
  to_port                      = 27017
}

resource "aws_vpc_security_group_ingress_rule" "db_ssh_from_app" {
  security_group_id            = aws_security_group.db.id
  description                  = "SSH somente via VM da aplicacao (bastion)"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 22
  to_port                      = 22
}

resource "aws_vpc_security_group_egress_rule" "db_all" {
  security_group_id = aws_security_group.db.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# ---------------------------------------------------------------------------
# Acesso: chave SSH e permissão do banco para gravar backups no S3
# ---------------------------------------------------------------------------
resource "aws_key_pair" "deployer" {
  key_name   = "${local.name_prefix}-deployer"
  public_key = var.ssh_public_key
}

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "db" {
  name               = "${local.name_prefix}-db-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

data "aws_iam_policy_document" "db_backup" {
  statement {
    sid       = "ListBackups"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.backup_bucket_name}"]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${var.project}/${var.environment}/*"]
    }
  }

  statement {
    sid       = "ReadWriteBackups"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["arn:aws:s3:::${var.backup_bucket_name}/${var.project}/${var.environment}/*"]
  }
}

resource "aws_iam_role_policy" "db_backup" {
  name   = "backup-s3"
  role   = aws_iam_role.db.id
  policy = data.aws_iam_policy_document.db_backup.json
}

resource "aws_iam_instance_profile" "db" {
  name = "${local.name_prefix}-db-profile"
  role = aws_iam_role.db.name
}

# ---------------------------------------------------------------------------
# Máquinas virtuais
# ---------------------------------------------------------------------------
resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
  key_name               = aws_key_pair.deployer.key_name

  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }

  # Mudança de tipo é aplicada no lugar (stop/start), sem recriar a VM.
  # Uma AMI nova publicada pela Canonical não deve recriar a VM: o SO é
  # atualizado pelo Ansible (update_os).
  lifecycle {
    ignore_changes = [ami]
  }

  tags = { Name = "${var.instance_name}-app", Role = "app" }
}

resource "aws_eip" "app" {
  domain   = "vpc"
  instance = aws_instance.app.id

  tags = { Name = "${local.name_prefix}-eip-app" }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_instance" "db" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.db_instance_type
  subnet_id                   = aws_subnet.db.id
  vpc_security_group_ids      = [aws_security_group.db.id]
  key_name                    = aws_key_pair.deployer.key_name
  iam_instance_profile        = aws_iam_instance_profile.db.name
  associate_public_ip_address = true # somente saída; SG não permite entrada da internet

  metadata_options {
    http_tokens = "required"
    # 2 saltos: o contêiner aws-cli do backup usa as credenciais da instância
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }

  lifecycle {
    ignore_changes = [ami]
  }

  tags = { Name = "${var.instance_name}-db", Role = "db" }
}

# Volume persistente dos dados do MongoDB: independe do disco do sistema e
# sobrevive à recriação do contêiner (e até da VM).
resource "aws_ebs_volume" "mongo_data" {
  availability_zone = local.az
  size              = var.db_volume_size
  type              = "gp3"
  encrypted         = true

  tags = { Name = "${local.name_prefix}-mongo-data" }
}

resource "aws_volume_attachment" "mongo_data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.mongo_data.id
  instance_id = aws_instance.db.id
}
