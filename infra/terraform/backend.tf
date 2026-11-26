# Estado remoto no S3 (criptografado, versionado e com lock nativo do S3).
# Bucket, chave e região são informados pela pipeline em "terraform init
# -backend-config=...", permitindo um estado separado por ambiente:
#   s3://<bucket>/todo-app/<environment>/terraform.tfstate
terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
