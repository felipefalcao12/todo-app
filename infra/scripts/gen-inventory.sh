#!/usr/bin/env bash
# Gera o inventário do Ansible a partir dos outputs do Terraform.
# Uso: gen-inventory.sh <outputs.json> <chave_privada> <saida.yml>
set -euo pipefail

OUT="${1:?outputs.json}"
KEY="${2:?caminho da chave}"
DEST="${3:?arquivo de saída}"

v() { jq -r ".$1.value" "$OUT"; }

APP_IP="$(v app_public_ip)"
cat > "$DEST" <<YAML
all:
  vars:
    ansible_user: ubuntu
    ansible_ssh_private_key_file: ${KEY}
    environment_name: $(v environment)
    app_domain: $(v app_domain)
    db_private_ip: $(v db_private_ip)
    db_public_ip: $(v db_public_ip)
    mongo_volume_id: $(v mongo_volume_id)
    backup_bucket: $(v backup_bucket)
    backup_prefix: $(v backup_prefix)
    aws_region: ${AWS_REGION:-us-east-1}
  children:
    app:
      hosts:
        app-vm:
          ansible_host: ${APP_IP}
    db:
      hosts:
        db-vm:
          ansible_host: $(v db_private_ip)
          ansible_ssh_common_args: >-
            -o ProxyCommand="ssh -W %h:%p -q -i ${KEY} -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=~/.ssh/known_hosts ubuntu@${APP_IP}"
YAML
echo "Inventário gerado: app=${APP_IP} db=$(v db_private_ip) (via bastion)"
