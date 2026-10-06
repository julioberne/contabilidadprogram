/* 🤝 Compendio para el cliente 13.6 — lógica pura. */
import { describe, it, expect } from 'vitest';
import {
  datosCompendio, validarCompendio, linkCompleto, textoWhatsApp, urlWhatsApp, haceCuanto,
  COMPENDIO_INICIAL, MAX_COMPENDIO,
} from './compendios.js';

describe('compendio para el cliente', () => {
  it('arma el cuerpo solo con lo usado', () => {
    expect(datosCompendio([4, 9], '  ', COMPENDIO_INICIAL)).toEqual({
      tx_ids: [4, 9], vigencia_dias: 15, identificacion: true, ubicaciones: true,
    });
    expect(datosCompendio([4], ' Viaje ', { ...COMPENDIO_INICIAL, nota: ' hola ', vigencia: 30, identificacion: false }))
      .toEqual({ tx_ids: [4], vigencia_dias: 30, identificacion: false, ubicaciones: true, nombre: 'Viaje', nota: 'hola' });
  });

  it('valida cantidad, vigencia y nota', () => {
    expect(validarCompendio(3, COMPENDIO_INICIAL)).toBeNull();
    expect(validarCompendio(0, COMPENDIO_INICIAL)).toMatch(/al menos/);
    expect(validarCompendio(MAX_COMPENDIO + 1, COMPENDIO_INICIAL)).toMatch(/Máximo/);
    expect(validarCompendio(3, { ...COMPENDIO_INICIAL, vigencia: 10 })).toMatch(/dura/);
    expect(validarCompendio(3, { ...COMPENDIO_INICIAL, nota: 'x'.repeat(1001) })).toMatch(/nota/);
  });

  it('link completo y WhatsApp sin enviar nada', () => {
    expect(linkCompleto('/c/abc', 'https://finsys-andres.duckdns.org/')).toBe('https://finsys-andres.duckdns.org/c/abc');
    expect(linkCompleto(null, 'https://x')).toBeNull();
    const texto = textoWhatsApp({ nombre: 'Viaje', folio: 'EXP-2026-0007', link: 'https://x/c/abc', expira_en: '2026-10-21T15:00:00Z' });
    expect(texto).toContain('Viaje (EXP-2026-0007)');
    expect(texto).toContain('https://x/c/abc');
    expect(urlWhatsApp('a b&c')).toBe('https://wa.me/?text=a%20b%26c');
  });

  it('hace cuánto', () => {
    const ahora = new Date('2026-10-06T12:00:00Z');
    expect(haceCuanto(null, ahora)).toBeNull();
    expect(haceCuanto('2026-10-06T11:55:00Z', ahora)).toBe('hace 5 min');
    expect(haceCuanto('2026-10-06T09:00:00Z', ahora)).toBe('hace 3 h');
    expect(haceCuanto('2026-10-05T12:00:00Z', ahora)).toBe('hace 1 día');
  });
});
