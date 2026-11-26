# Versão fixa e reproduzível do MongoDB (evita "latest")
FROM mongo:7.0

COPY ./init-mongo.js /docker-entrypoint-initdb.d/

EXPOSE 27017
