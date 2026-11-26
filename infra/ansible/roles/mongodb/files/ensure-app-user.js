// Garante que o usuário da aplicação exista com a senha atual (secret).
// Imprime CHANGED somente quando algo foi alterado (idempotência no Ansible).
const dbName = process.env.MONGO_INITDB_DATABASE || 'todo-app';
const user = process.env.MONGO_APP_USER;
const pwd = process.env.MONGO_APP_PASSWORD;
const appDb = db.getSiblingDB(dbName);

const existing = appDb.getUser(user);
if (!existing) {
  appDb.createUser({ user, pwd, roles: [{ role: 'readWrite', db: dbName }] });
  print('CHANGED: usuário criado');
} else {
  // Testa a senha atual sem alterar nada
  let ok = false;
  try {
    const conn = new Mongo('mongodb://127.0.0.1:27017');
    ok = conn.getDB(dbName).auth(user, pwd).ok === 1;
  } catch (e) {
    ok = false;
  }
  if (!ok) {
    appDb.updateUser(user, { pwd });
    print('CHANGED: senha atualizada');
  } else {
    print('OK: usuário existente');
  }
}
