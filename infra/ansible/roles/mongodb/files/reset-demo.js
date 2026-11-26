// Preparação intencional de uma nova lista para a apresentação.
const dbName = process.env.MONGO_INITDB_DATABASE || 'todo-app';
const todos = db.getSiblingDB(dbName).todos;
const removed = todos.deleteMany({}).deletedCount;
todos.insertMany([
  { text: "Laércio é um excelente professor", completed: false },
  { text: "Estudar Cloud", completed: true },
  { text: "Fazer exercícios da UA", completed: false },
]);
print(`Lista reiniciada: ${removed} tarefa(s) removida(s), ${todos.countDocuments()} tarefa(s) de demonstração.`);
