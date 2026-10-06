# SPEC 13 — Análisis Inteligente

> **Módulo:** 13 Análisis Inteligente · **Nivel:** módulo · **Estado:** EN USO (hitos 1–3 en producción; 13.4 y 13.5 planificados)
> **Versión:** 1.1 — 05 Oct 2026 · **Reglas que aplican:** 2 (Zero-Impact), 6b
> **Qué NO cubre:** el registro de movimientos por chat (módulo 09); los asientos de partida doble y su flujo de aprobación (kernel / módulo 12); reconciliación banco-vs-libro (flujo manual de Andrés — no se tocan saldos).
> Investigación de origen: [artefacto "Mejor que Excel"](https://claude.ai/artifact/B8tTdibRt6gnyaDoYQk3nN) (2 rondas, 46 fuentes) · plan aprobado 15-sep: `~/.claude/plans/merry-finding-storm.md`. Estado vivo: `CHECKLIST.md` fila 13.

## 1. Objetivo
Convertir a FIN-SYS de un sistema de REGISTRO en un sistema de RESPUESTAS: el usuario recibe avisos sin pedirlos (insights), explora libremente (pivot Perspective), pregunta en español (web y bot) y se lleva los libros en Excel real — sin que ninguna cifra nazca de una IA.

## 2. Alcance
**Incluye:** catálogo único de métricas whitelisted, motor de insights, módulo web "Análisis" (∑) con Perspective, preguntas en español con gráfica server-side, comandos informativos del bot (`/analisis`, `/resumen`), bitácora de preguntas sin responder, exportación .xlsx.
**Excluye:** Metabase (en la banca — decisión 15-sep), RAG con pgvector (fase posterior, si el catálogo desborda el prompt), grafos de conocimiento (descartados), escrituras de cualquier tipo (el módulo es 100 % lectura).

## 3. Requisitos del módulo (criterios inmutables del plan aprobado)
| ID | Requisito | Origen |
|---|---|---|
| R-13-01 | Ninguna cifra nace de una IA: solo funciones del catálogo, auditables (SQL visible). | Plan 15-sep, criterio 1 |
| R-13-02 | La empresa va amarrada por código en cada consulta; jamás la decide el LLM (params fuera de whitelist se descartan). | Plan 15-sep, criterio 2 |
| R-13-03 | Toda respuesta lleva sello de origen ("según N TXs de <rango>"). | Plan 15-sep, criterio 3 |
| R-13-04 | Errores honestos: si no hay datos suficientes se dice; nunca se rellena. Preguntas sin responder quedan en bitácora. | Plan 15-sep, criterio 4 |
| R-13-05 | Telegram = informativo (texto + imagen); la web = interactivo. | Plan 15-sep, criterio 5 |
| R-13-06 | USD jamás se suma al COP; se cuenta aparte (`origen.usd_excluidas`). | D 16-sep |

## 4. Arquitectura
```
                     ┌─ metrics_catalog.py (9 métricas whitelisted + SQL auditable) ─┐
                     │              ejecutar_metrica() = punto único                 │
                     ▼                                                              ▼
        insight_engine.py (reglas SOBRE el catálogo)              analytics_qa.py (responder_pregunta)
             │                                                         │  ▲
             │                                                         │  └ ai_engine.structure_analytics_question
             ▼                                                         ▼     (Groq json_object → {funcion, params}; solo TRADUCE)
  GET /api/analytics/insights                            POST /api/analytics/ask → texto + PNG matplotlib (Figure sin pyplot)
             │                                                         │
     HomeDashboard (tarjetas)                     AnalisisApp (web) ── bot_driver `/analisis` `/resumen` (foto vía send_photo)
             └── tick_resumen_telegram (poller, reloj en BD) ── 📊 resumen cada 24 h a chats vinculados

  GET /api/analytics/dataset (plano de obtener_transacciones) ──▶ Perspective 3.8 WASM (módulo ∑, pivot en el navegador)
```
**Tablas propias**: `analytics_question_log` (bitácora, retención 30 días, purga en cada INSERT).
**Endpoints propios** (`routers/analytics.py`, todos `require_auth`): `/api/analytics/catalog`, `/metric`, `/dataset`, `/ask`, `/insights`, `/preguntas-log`.
**Frontend**: `frontend/src/analisis/` (módulo 13 «∑» del registry, chunk perezoso).

## 5. Decisiones de módulo
| ID | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D-13-01 | Construir EN CASA sobre catálogo whitelisted; el LLM solo elige del menú. | Metabase AI (guardarraíl "solo verificado" es de pago), WrenAI (congelada sin parches), text-to-SQL libre | Alucinación de cifras y fuga entre empresas: imposibles por construcción; ~$0/pregunta. |
| D-13-02 | Perspective 3.8: los 3 WASM por `?url` + tríada init en `perspectiveBoot.js`; chunk perezoso propio. | Builds `.inline.js` (~7 MB base64); grupos de chunk en vite.config | Lección RRHH: JAMÁS separar dependencias de un chunk en grupos (import circular). |
| D-13-03 | Gráficas server-side con matplotlib `Figure` sin pyplot (`MPLBACKEND=Agg`). | Gráfica en el cliente; QuickChart | Thread-safe con gunicorn; el MISMO motor sirve a web y bot (R-13-05). |
| D-13-04 | Metabase queda EN LA BANCA (opcional futuro). | Metabase como pieza central | BYOK sin Groq (solo puente OpenRouter), Agent API sin imágenes, guardarraíl paywalled. |
| D-13-05 | Sin scheduler: el resumen Telegram usa un tick del poller con reloj persistido en BD (`bot_messages` kind `resumen_analytics`). | cron / APScheduler | Sobrevive reinicios, jamás tumba el poller, cero infra nueva. |

## Etapas (hitos)
| Hito | Qué | Estado | Spec |
|---|---|---|---|
| 1 | B0+B2+B3: catálogo (9 métricas + SQL visible), módulo web ∑ con Perspective, preguntas en español con gráfica y sello | ✅ en producción 16-sep-2026 (`548e5f8`) | plan `merry-finding-storm.md` + `docs/checkpoints.md` |
| 2 | B1: insights automáticos en Home + 📊 resumen Telegram cada 24 h + bitácora UI + métrica `conteo_terceros` | ✅ en producción 22-sep-2026 (`dfdf9f1`) | `docs/checkpoints.md` 2026-09-21/22 |
| 3 | B4: bot informativo — `/analisis <pregunta>` (con foto) y `/resumen`, comandos explícitos (Regla 6b) | ✅ en producción 22-sep-2026 (`6468d8d`, deploy `30e3aa7`) | `docs/checkpoints.md` 2026-09-22 |
| **4** | **B5 motor: exportación integral .xlsx — los 10 libros del contador (openpyxl), con entrada selectiva + relación de transacciones elegidas** | ✅ en producción 05-oct-2026 (`bf03177`) | [13.4-export-xlsx.md](13.4-export-xlsx.md) |
| **5** | **B5 interfaz: ⇩ EXPORTACIÓN (desde el 06-oct módulo 14 propio en el registry, ruta `/exportacion`; nació como desplegable dentro de ∑) — organizador contable con el patrón del de RRHH (carpetas, tipos documentales, vista previa, subir soportes) + exportación selectiva por período (paquetes) o por transacciones elegidas (también desde el Libro Diario) + folio, huella, vigencia y vista 🗓 cierres** | 🟡 EN CONSTRUCCIÓN — aprobado 05-oct; 13.5-a backend y 13.5-b organizador web HECHOS (05-oct); faltan 13.5-c y 13.5-d | [13.5-submodulo-exportacion.md](13.5-submodulo-exportacion.md) |
| 6 | Comparativos, formatos de importación a software contable, 📤 envío al chat, exportar la vista del explorador | 💡 propuesto | §11 de 13.5 |
| — | pgvector si el catálogo desborda el prompt | ⏳ sin abrir | — |

## Deuda de documentación del módulo
Los endpoints `/api/analytics/*` no tienen ancla en `docs/api_spec.md` ni `analytics_question_log` en `docs/database_schema.md` (los hitos 1–3 se cerraron antes de existir el sistema de specs). Se completan al cerrar 13.4/13.5 junto con lo nuevo.
