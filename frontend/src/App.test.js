import { render, screen } from '@testing-library/react';
import axios from 'axios';
import App from './App';

// A API é simulada: o teste valida a interface sem depender do backend.
jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
  patch: jest.fn(),
  delete: jest.fn(),
}));

beforeEach(() => {
  axios.get.mockResolvedValue({ data: [{ _id: '1', text: 'Tarefa de teste', completed: false }] });
});

test('renderiza o título e a lista retornada pela API', async () => {
  render(<App />);
  expect(screen.getByText(/lista de tarefas/i)).toBeInTheDocument();
  expect(await screen.findByText('Tarefa de teste')).toBeInTheDocument();
  expect(axios.get).toHaveBeenCalledWith('/todos');
});
