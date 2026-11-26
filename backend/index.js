const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const bodyParser = require('body-parser');

// ---------------------------------------------------------------------------
// Configuração por ambiente (nada de credencial fixa no código)
// ---------------------------------------------------------------------------
const port = Number(process.env.PORT || 5000);
const mongoUrl = process.env.MONGO_URL;
const corsOrigin = process.env.CORS_ORIGIN || '';
const appVersion = process.env.APP_VERSION || 'dev';

if (!mongoUrl) {
  console.error('Variável MONGO_URL não definida. Encerrando.');
  process.exit(1);
}

const app = express();

// CORS restrito: em produção frontend e API usam o mesmo endereço (Nginx),
// então só liberamos origens explicitamente configuradas.
if (corsOrigin) {
  app.use(cors({ origin: corsOrigin.split(',').map((o) => o.trim()) }));
}
app.use(bodyParser.json({ limit: '10kb' }));

// ---------------------------------------------------------------------------
// Conexão com o MongoDB com novas tentativas (o banco pode subir depois da API)
// ---------------------------------------------------------------------------
mongoose.set('strictQuery', true);

async function connectWithRetry(attempt = 1) {
  try {
    await mongoose.connect(mongoUrl, { serverSelectionTimeoutMS: 5000 });
    console.log('Conectado ao MongoDB');
  } catch (err) {
    const wait = Math.min(30, attempt * 2);
    // Mensagem sem a URL para não expor credenciais nos logs
    console.error(`Erro ao conectar ao MongoDB (tentativa ${attempt}): ${err.name}. Nova tentativa em ${wait}s`);
    setTimeout(() => connectWithRetry(attempt + 1), wait * 1000);
  }
}

mongoose.connection.on('disconnected', () => console.warn('MongoDB desconectado'));
mongoose.connection.on('reconnected', () => console.log('MongoDB reconectado'));

// ---------------------------------------------------------------------------
// Modelo
// ---------------------------------------------------------------------------
const TodoSchema = new mongoose.Schema({
  text: { type: String, required: true, maxlength: 200 },
  completed: { type: Boolean, default: false },
});

const Todo = mongoose.model('Todo', TodoSchema);

// ---------------------------------------------------------------------------
// Saúde: só responde 200 se a API estiver conectada ao banco (REQ-06)
// ---------------------------------------------------------------------------
app.get('/health', async (req, res) => {
  const state = mongoose.connection.readyState; // 1 = conectado
  if (state !== 1) {
    return res.status(503).json({ status: 'erro', database: 'desconectado', version: appVersion });
  }
  try {
    await mongoose.connection.db.admin().ping();
    return res.json({ status: 'ok', database: 'conectado', version: appVersion });
  } catch (err) {
    return res.status(503).json({ status: 'erro', database: 'sem resposta', version: appVersion });
  }
});

// Rota para obter todas as tarefas (GET)
app.get('/todos', async (req, res) => {
  try {
    const todos = await Todo.find();
    res.json(todos);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// Rota para adicionar uma nova tarefa (POST)
app.post('/todos', async (req, res) => {
  const { text } = req.body;

  if (!text) {
    return res.status(400).json({ message: 'O campo "text" é obrigatório' });
  }

  const todo = new Todo({ text, completed: false });

  try {
    const newTodo = await todo.save();
    res.status(201).json(newTodo);
  } catch (err) {
    res.status(400).json({ message: err.message });
  }
});

// Rota para alternar o estado da tarefa (PATCH)
app.patch('/todos/:id', async (req, res) => {
  try {
    const todo = await Todo.findById(req.params.id);

    if (!todo) {
      return res.status(404).json({ message: 'Tarefa não encontrada' });
    }

    todo.completed = !todo.completed;
    await todo.save();
    res.json(todo);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// Rota para excluir uma tarefa (DELETE)
app.delete('/todos/:id', async (req, res) => {
  try {
    const todo = await Todo.findByIdAndDelete(req.params.id);

    if (!todo) {
      return res.status(404).json({ message: 'Tarefa não encontrada' });
    }

    res.json({ message: 'Tarefa excluída com sucesso' });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

const server = app.listen(port, () => {
  console.log(`Servidor rodando na porta ${port} (versão ${appVersion})`);
  connectWithRetry();
});

// Encerramento limpo (docker stop / restart)
function shutdown(signal) {
  console.log(`${signal} recebido, encerrando...`);
  server.close(() => mongoose.connection.close(false).then(() => process.exit(0)));
  setTimeout(() => process.exit(0), 10000).unref();
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
