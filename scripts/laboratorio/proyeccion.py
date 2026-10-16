# -*- coding: utf-8 -*-
"""Proyección de capacidad (laboratorio de rendimiento).

MODELO, no medición: parte de lo medido (EXPLAIN ANALYZE, carga acotada,
pool) y extrapola a más filas y usuarios con supuestos explícitos.

- Trabajo en BD de una consulta con N transacciones por empresa:
      S(N) = S0 + k · c · max(0, N − N0)
  S0 = tiempo medido hoy, k = cuántas veces el plan recorre `transactions`
  entera (Seq Scan), c = costo por fila recorrida (SUPUESTO: 2 µs, típico de
  Postgres filtrando/ordenando en memoria; con CPU compartida puede ser más).
  Si el plan usa índices (k = 0), S(N) ≈ S0 (crece como log N: se ignora).
- Cota PESIMISTA: con tablas chicas Postgres recorre todo aunque haya índice;
  a gran escala puede elegir índices que hoy no usa. Lo que siempre recorre
  todo (p. ej. una función de ventana sobre la tabla entera) sí escala así.
- Capacidad (Ley de Little): consultas/s ≈ conexiones útiles / (S(N) + 20 ms
  fijos por petición, SUPUESTO de producción).
  Conexiones útiles = workers × pool, recortado al 80 % de max_connections.
- Usuarios activos ≈ consultas/s × segundos entre consultas de un usuario
  (SUPUESTO: 3 s con debounce y tiempo de leer).
- Carga útil de catálogos completos: crece lineal con las filas.
"""
from typing import Dict, List, Optional

COSTO_FILA_S = 2e-6          # supuesto: 2 µs por fila recorrida
SOBRECOSTO_S = 0.020         # supuesto: 20 ms fijos por petición (framework + red VPS↔Supabase)
PAUSA_USUARIO_S = 3.0        # supuesto: un usuario activo hace 1 consulta cada 3 s
ESCALAS = (50_000, 500_000, 5_000_000)
PRESUPUESTO_KB_INTERACTIVO = 200


def conexiones_utiles(workers: int, pool_max: int, max_connections: Optional[int]) -> int:
    c = workers * pool_max
    if max_connections:
        c = min(c, int(0.8 * max_connections))
    return max(1, c)


def recorridos_transacciones(plan: dict) -> int:
    return sum(1 for s in plan.get("seq_scans", []) if s.get("tabla") == "transactions")


def trabajo_bd_ms(s0_ms: float, k: int, n: int, n0: int) -> float:
    return s0_ms + k * COSTO_FILA_S * max(0, n - n0) * 1000.0


def proyectar(planes: List[dict], n0: int, workers: int, pool_max: int,
              max_connections: Optional[int], escalas=ESCALAS) -> dict:
    conns = conexiones_utiles(workers, pool_max, max_connections)
    filas = []
    for n in (n0, *escalas):
        por_consulta = {}
        for p in planes:
            if "error" in p:
                continue
            k = recorridos_transacciones(p)
            por_consulta[p["consulta"]] = round(trabajo_bd_ms(p["ejecucion_ms"], k, n, n0), 1)
        if not por_consulta:
            continue
        peor = max(por_consulta, key=por_consulta.get)
        s_peor = por_consulta[peor] / 1000.0 + SOBRECOSTO_S
        qps = conns / max(s_peor, 1e-4)
        filas.append({"transacciones_por_empresa": n, "ms_por_consulta": por_consulta,
                      "consulta_mas_lenta": peor, "consultas_por_s": round(qps, 1),
                      "usuarios_activos": int(qps * PAUSA_USUARIO_S)})
    return {"conexiones_utiles": conns, "supuestos": {"costo_fila_us": COSTO_FILA_S * 1e6,
            "pausa_usuario_s": PAUSA_USUARIO_S, "sobrecosto_ms": SOBRECOSTO_S * 1000,
            "workers": workers, "pool_max": pool_max},
            "escalas": filas}


def proyectar_carga_util(kb_hoy: Dict[str, float], filas_hoy: Dict[str, int],
                         escalas=ESCALAS) -> List[dict]:
    """Endpoints de catálogo completo: KB a cada escala (lineal con sus filas)."""
    out = []
    for nombre, kb in kb_hoy.items():
        base = max(1, filas_hoy.get(nombre, 1))
        out.append({"endpoint": nombre, "kb_hoy": kb,
                    "kb_proyectado": {n: round(kb * n / base, 0) for n in escalas},
                    "excede_presupuesto_en": next((n for n in escalas if kb * n / base > PRESUPUESTO_KB_INTERACTIVO), None)})
    return out
