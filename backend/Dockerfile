FROM node:18-alpine

WORKDIR /app

# Dependências de produção, instaladas de forma reproduzível pelo lockfile
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY . .

ARG APP_VERSION=dev
ENV NODE_ENV=production \
    PORT=5000 \
    APP_VERSION=${APP_VERSION}

# Executa sem privilégios de root
USER node

EXPOSE 5000

# Verificação de saúde que inclui a conexão com o MongoDB
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:5000/health || exit 1

CMD ["node", "index.js"]
