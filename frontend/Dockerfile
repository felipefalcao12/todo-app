# Etapa 1: construção da aplicação React
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Versão exibida no rodapé (tag da imagem)
ARG APP_VERSION=dev
ENV REACT_APP_VERSION=${APP_VERSION}

RUN npm run build

# Etapa 2: Nginx servindo o build e encaminhando a API
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/nginx-health || exit 1

CMD ["nginx", "-g", "daemon off;"]
