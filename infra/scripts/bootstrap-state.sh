#!/usr/bin/env bash
# Cria (uma única vez) os buckets que ficam FORA do estado do Terraform:
#   - pm04-tfstate-<conta>: estado remoto, versionado e criptografado
#   - pm04-backups-<conta>: backups do MongoDB (sobrevivem ao destroy)
# Idempotente: se os buckets já existem, apenas confere as configurações.
set -euo pipefail

REGION="${AWS_REGION:?defina AWS_REGION}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
STATE_BUCKET="pm04-tfstate-${ACCOUNT_ID}"
BACKUP_BUCKET="pm04-backups-${ACCOUNT_ID}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

ensure_bucket() {
  local bucket="$1"
  if aws s3api head-bucket --bucket "$bucket" 2>/dev/null; then
    echo "Bucket ${bucket} já existe"
  else
    echo "Criando bucket ${bucket} em ${REGION}"
    if [ "$REGION" = "us-east-1" ]; then
      aws s3api create-bucket --bucket "$bucket" --region "$REGION" >/dev/null
    else
      aws s3api create-bucket --bucket "$bucket" --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
    fi
  fi
  aws s3api put-public-access-block --bucket "$bucket" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-encryption --bucket "$bucket" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-bucket-versioning --bucket "$bucket" --versioning-configuration Status=Enabled
}

ensure_bucket "$STATE_BUCKET"
ensure_bucket "$BACKUP_BUCKET"

# Retenção dos backups (e das versões antigas do estado)
aws s3api put-bucket-lifecycle-configuration --bucket "$BACKUP_BUCKET" --lifecycle-configuration "{
  \"Rules\":[{\"ID\":\"retencao-backups\",\"Status\":\"Enabled\",\"Filter\":{\"Prefix\":\"\"},
  \"Expiration\":{\"Days\":${BACKUP_RETENTION_DAYS}},
  \"NoncurrentVersionExpiration\":{\"NoncurrentDays\":7}}]}"
aws s3api put-bucket-lifecycle-configuration --bucket "$STATE_BUCKET" --lifecycle-configuration '{
  "Rules":[{"ID":"versoes-antigas-estado","Status":"Enabled","Filter":{"Prefix":""},
  "NoncurrentVersionExpiration":{"NoncurrentDays":90}}]}'

if [ -n "${GITHUB_ENV:-}" ]; then
  {
    echo "TF_STATE_BUCKET=${STATE_BUCKET}"
    echo "BACKUP_BUCKET=${BACKUP_BUCKET}"
  } >> "$GITHUB_ENV"
fi
echo "Estado: s3://${STATE_BUCKET} | Backups: s3://${BACKUP_BUCKET} (retenção ${BACKUP_RETENTION_DAYS} dias)"
