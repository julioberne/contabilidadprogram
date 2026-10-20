import { describe, expect, it, vi } from 'vitest';
import { esperarOperacion } from './operaciones.js';

const resp = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body });

describe('esperarOperacion', () => {
  it('sigue consultando hasta HECHA y devuelve el resultado', async () => {
    const pedir = vi.fn()
      .mockResolvedValueOnce(resp(200, { estado: 'PENDIENTE' }))
      .mockResolvedValueOnce(resp(503, {}))                       // pasajero: no corta
      .mockResolvedValueOnce(resp(200, { estado: 'EN_CURSO' }))
      .mockResolvedValueOnce(resp(200, { estado: 'HECHA', resultado: { id: 7 } }));
    const estados = [];
    const r = await esperarOperacion(3, { pedir, esperar: async () => {}, onEstado: (op) => estados.push(op.estado) });
    expect(r).toEqual({ id: 7 });
    expect(pedir).toHaveBeenCalledTimes(4);
    expect(pedir.mock.calls[0][0]).toMatch(/\/operaciones\/3$/);
    expect(estados).toEqual(['PENDIENTE', 'EN_CURSO', 'HECHA']);
  });

  it('FALLIDA lanza el motivo y un 404 no se reintenta', async () => {
    const fallida = vi.fn().mockResolvedValue(resp(200, { estado: 'FALLIDA', error: 'receta inválida' }));
    await expect(esperarOperacion(1, { pedir: fallida, esperar: async () => {} })).rejects.toThrow('receta inválida');
    const noExiste = vi.fn().mockResolvedValue(resp(404, {}));
    await expect(esperarOperacion(1, { pedir: noExiste, esperar: async () => {} })).rejects.toThrow('ya no existe');
    expect(noExiste).toHaveBeenCalledTimes(1);
  });

  it('se rinde con un aviso cuando pasa el tiempo máximo', async () => {
    const pedir = vi.fn().mockResolvedValue(resp(200, { estado: 'EN_CURSO' }));
    await expect(esperarOperacion(1, { pedir, esperar: async () => {}, maxMs: -1 })).rejects.toThrow('organizador');
  });
});
