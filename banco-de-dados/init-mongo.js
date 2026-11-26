// Executado pelo entrypoint oficial do MongoDB somente na primeira
// inicialização (diretório de dados vazio).
// 1) cria o usuário próprio da aplicação (sem privilégios administrativos)
// 2) insere os dados iniciais de demonstração
const dbName = process.env.MONGO_INITDB_DATABASE || 'todo-app';
const appUser = process.env.MONGO_APP_USER || 'todo_app';
const appPassword = process.env.MONGO_APP_PASSWORD;

db = db.getSiblingDB(dbName);

if (appPassword) {
  db.createUser({
    user: appUser,
    pwd: appPassword,
    roles: [{ role: 'readWrite', db: dbName }],
  });
  print(`Usuário da aplicação "${appUser}" criado em ${dbName}`);
} else {
  print('MONGO_APP_PASSWORD não definida: usuário da aplicação não criado');
}

db.createCollection('todos');

db.todos.insertMany([
  { text: "Laércio é um excelente professor", completed: false },
  { text: "Estudar Cloud", completed: true },
  { text: "Fazer exercícios da UA", completed: false },
]);
