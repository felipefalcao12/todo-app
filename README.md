# ToDo App

Aplicação de lista de tarefas utilizada nos laboratórios de Engenharia de Software do professor Laércio. O objetivo do laboratório é trabalhar a implantação de uma aplicação em nuvem, partindo de um sistema já desenvolvido.

A aplicação permite cadastrar, listar, concluir, reabrir e excluir tarefas. Ela foi trazida do repositório `aula-uniamerica-infraestrutura-cloud` como base para este novo laboratório.

## Escopo para a Feira de Profissões

O cenário da atividade apresenta o projeto desenvolvido por alunos do 3º período de Engenharia de Software e a contratação de um profissional para implantá-lo na nuvem para a feira.

Consulte o [escopo em PDF](escopo.pdf) ou a [versão editável](docs/escopo.md), com arquitetura, automação, custos, entregáveis e critérios de aceite. O [fluxo proposto da aplicação](docs/assets/fluxo-aplicacao.pdf) também está disponível separadamente. Para gerar os PDFs, instale a dependência de documentação `reportlab` e execute `python scripts/render-escopo.py`.

## Implantação na nuvem (PM04 · Terraform + Ansible + GitHub Actions)

A aplicação é implantada na AWS em **duas VMs** (aplicação e MongoDB isolado), com HTTPS público, backups no S3 e todas as mudanças operadas por pipelines.

| Documento | Conteúdo |
|---|---|
| [docs/pm04/arquitetura.md](docs/pm04/arquitetura.md) | Análise da demanda, arquitetura, decisões, parâmetros, custos e limitações |
| [docs/pm04/manual-operacao.md](docs/pm04/manual-operacao.md) | Secrets, rotinas (saúde, logs, reinício, backup, restauração, limpeza da lista, desativação) e diagnóstico |
| [docs/pm04/roteiro-testes.md](docs/pm04/roteiro-testes.md) | Cenários 1, 2 e 3 do PM04 e evidências de aceite |

```text
.github/workflows/  app-ci.yml (imagens) · infra.yml (Terraform → Ansible) · ops.yml (rotinas) · destroy.yml
.github/actions/    terraform-setup · ansible-setup (ações reutilizadas pelos workflows)
infra/terraform/    VPC, sub-redes, security groups, 2 VMs, EBS de dados, Elastic IP, IAM (estado no S3)
infra/ansible/      roles: common, os_updates, docker, mongodb, backup, app · playbooks: site.yml, ops.yml
infra/scripts/      bootstrap do estado/backups e geração do inventário
evidencias/         prints das execuções
```

Início rápido: cadastre os secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `SSH_PRIVATE_KEY`, `MONGO_ROOT_PASSWORD` e `MONGO_APP_PASSWORD`; rode **App · Validar, construir e publicar imagens** com `version=v1.0.0`; depois **Infra · Provisionar e configurar** com `action=apply`. A URL aparece no resumo da execução.

## Executar localmente

Pré-requisitos: Git e Docker com Docker Compose. No Windows, execute o Docker Desktop com containers Linux antes de iniciar.

1. Abra um terminal na pasta deste repositório:

   ```bash
   cd todo-app
   ```

2. Crie o arquivo de variáveis e defina as senhas:

   ```bash
   cp .env.example .env
   ```

3. Construa as imagens e inicie os serviços:

   ```bash
   docker compose up --build -d
   ```

4. Confira os serviços e acompanhe os logs:

   ```bash
   docker compose ps
   docker compose logs -f
   ```

   Aguarde a mensagem `Conectado ao MongoDB` no backend. Use `Ctrl+C` para sair dos logs; os serviços continuam rodando.

5. Acesse a aplicação em **http://localhost**. A API responde pelo mesmo endereço em **http://localhost/todos** e a saúde em **http://localhost/health**.

6. Cadastre uma tarefa, clique no texto para concluir ou reabrir e use **Excluir** para removê-la. Atualize a página para conferir os dados retornados pela API.

7. Ao terminar, pare os serviços:

   ```bash
   docker compose down
   ```

A porta 80 precisa estar disponível na máquina (API e banco não são publicados). Caso seu ambiente use o executável legado, substitua `docker compose` por `docker-compose`.

## Estrutura

- `frontend/`: interface React, compilada e servida pelo Nginx.
- `backend/`: API Node.js com Express e Mongoose.
- `banco-de-dados/`: imagem MongoDB e script de criação dos dados iniciais.
- `docker-compose.yaml`: execução dos três serviços na rede local `todo-net`.

O navegador acessa o frontend e envia as operações para a API. A API consulta e atualiza o MongoDB.

```text
Navegador -> Nginx/Frontend (porta 80) -> /todos -> API Express (5000) -> MongoDB (27017)
```

## Base do laboratório de nuvem

O frontend usa caminhos relativos (`/todos`) e o Nginx encaminha a API; a conexão com o banco vem de `MONGO_URL`, com usuário próprio da aplicação. O Compose local usa volume nomeado e não publica o banco. As mudanças estão descritas em [docs/pm04/arquitetura.md](docs/pm04/arquitetura.md#4-adaptações-feitas-no-projeto-sem-alterar-regras-de-negócio).
