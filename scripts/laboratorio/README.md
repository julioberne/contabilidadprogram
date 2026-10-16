# Laboratorio de rendimiento y escalabilidad

Mide FIN-SYS con seis criterios y una proyección, aplica los umbrales del
estándar (`docs/estandar-consultas-escalables.md`) y escribe un informe con
veredicto en `docs/laboratorio/` (más `historial.jsonl` para la tendencia).
Todo es **solo lectura** contra la BD compartida con producción.

| # | Criterio | Script |
|---|---|---|
| 1 | Latencia por endpoint (p50/p95/p99, neta de red) | `carga_acotada.py` |
| 2 | Capacidad, errores y **pausas globales** | `carga_acotada.py` |
| 3 | Pool y conexiones | `/api/health/profundo` + `observatorio_bd.py` |
| 4 | Base de datos: pg_stat_statements, recorridos completos, índices, planes | `observatorio_bd.py` |
| 5 | Carga útil (KB por respuesta) y su proyección | `carga_acotada.py` + `proyeccion.py` |
| 6 | Auditoría del código con trinquete (también en el CI) | `auditoria_codigo.py` |
| + | Proyección de capacidad (modelo con supuestos explícitos) | `proyeccion.py` |

## Comandos (PowerShell, desde la raíz del repo)

```powershell
.venv\Scripts\python.exe scripts\laboratorio\laboratorio.py                 # auditoría + BD + proyección
.venv\Scripts\python.exe scripts\laboratorio\laboratorio.py --carga         # + carga acotada (21:00–07:00)
$env:LAB_TOKEN = "<token de tu sesión>"; .venv\Scripts\python.exe scripts\laboratorio\laboratorio.py --carga --url https://finsys-andres.duckdns.org
.venv\Scripts\python.exe scripts\laboratorio\auditoria_codigo.py --actualizar-linea-base   # tras pagar deuda
```

El token de sesión es el valor `finsys_session` del navegador con tu sesión abierta.

## Frenos de la carga (no negociables por argumento)
Solo GET · máximo 20 usuarios virtuales y 60 s por escalón · se detiene sola si
el p95 pasa de 1,5 s, si los errores pasan del 2 % o si el pool pasa del 70 % ·
por defecto solo de 21:00 a 07:00 (`--ahora` lo salta).

## Volumen grande (500.000+ filas)
No se prueba en producción (habría que escribir datos sintéticos). Sin Docker:
un proyecto de Supabase aparte ("finsys-lab"), con sus datos en `scratch/lab.env`
(`LAB_DB_HOST`, `LAB_DB_PORT`, `LAB_DB_USER=postgres.<ref>`, `LAB_DB_PASSWORD`,
`LAB_DB_NAME`) y `scripts/carga/` con `--lab-env scratch/lab.env`. La guarda
`_seguro.py` rechaza el usuario de producción.

## Agente
`.claude/agents/laboratorio-rendimiento.md`: córrelo antes de publicar un hito
que toque consultas, listas, el pool o pantallas que cargan datos.
