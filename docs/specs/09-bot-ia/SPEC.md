# SPEC 09 — Bot IA (registro contable por chat)

> **Módulo:** 09 Bot IA · **Nivel:** módulo · **Estado:** EN USO (etapas A–E en producción; F en curso)
> **Versión:** 1.0 — 22 Sep 2026 · **Reglas que aplican:** 2 (Zero-Impact), 5, 6, **6b**, 7
> **Qué NO cubre:** la web de la bandeja (`frontend/src/bot/`) más allá de lo que cada etapa toque; las preguntas en español ("¿cuánto gasté?") pertenecen al módulo 13.
> Referencia operativa (comandos, modelos, diagnóstico): [`docs/bot_ia.md`](../../bot_ia.md). Estado vivo: `CHECKLIST.md` fila 09.

## 1. Objetivo
Que cualquier movimiento de dinero llegue a la contabilidad **como borrador** desde el canal donde ocurre (chat, voz, foto, SMS del banco) y que **una persona lo confirme** antes de que toque el libro. El bot traduce; nunca calcula ni decide.

## 2. Alcance
**Incluye:** adaptador Telegram (long-polling, proceso único), núcleo canal-agnóstico, borradores con máquina de estados, evidencias (fotos, ubicación), etiquetas, vinculación chat↔usuario, e ingesta automática de fuentes externas (SMS).
**Excluye:** WhatsApp (etapa D, requiere dominio+TLS), consultas analíticas (módulo 13), asientos contables (kernel / módulo 12).

## 3. Requisitos del módulo
| ID | Requisito | Origen |
|---|---|---|
| R-09-01 | Ninguna escritura contable sin confirmación humana explícita (`Confirmar #N` o botón ✅). | Regla 6 |
| R-09-02 | Todo dato del borrador nace de un campo estructurado de la web o se pide a mano; sin heurísticas, pistas ni aprendizaje. | Regla 6b (22-sep-2026) |
| R-09-03 | Solo chats vinculados a un `hub_user` operan; un solo poller por token. | `docs/bot_ia.md` §4 |
| R-09-04 | Lo que el bot no entiende se conserva (borrador "no reconocido" o mensaje registrado), nunca se descarta en silencio. | Regla 6b |
| R-09-05 | Datos temporales con retención definida (30/60/90) y purga sin scheduler. | Regla 6b |

## 4. Arquitectura
```
Telegram ──getUpdates──▶ bot_telegram.py (poller, proceso único, envía TODO lo que sale a Telegram)
                              │ handle_message / handle_callback
                              ▼
                        bot_driver.py (núcleo canal-agnóstico) ── draft_builder.py (payload determinista) ── ai_engine.py (LLM solo para texto/voz libre)
                              │
                        transaction_drafts ── confirmar_draft ──▶ transaction_service.create_transaction (pipeline oficial + asiento kernel)

Fuentes externas (SMS) ──POST /api/webhooks/sms──▶ FastAPI (routers/webhooks_sms.py) ──▶ bot_messages(channel='sms')
                                                                                            └─ tick del poller ──▶ bot_sms.py ──▶ transaction_drafts ──▶ Telegram
```
**Tablas propias** (DDL en `docs/database_schema.md`): `bot_chat_links`, `bot_link_codes`, `bot_messages`, `transaction_drafts`, `transaction_evidences`, `sms_ingest_tokens` (09.F).
**Endpoints propios** (`docs/api_spec.md`): `/api/bot/*` (bandeja, vinculación) y `/api/webhooks/sms*` (09.F).

## 5. Decisiones de módulo
| ID | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D-09-01 | Un solo proceso envía a Telegram: el poller. FastAPI nunca llama a `sendMessage`. | Enviar desde el request del webhook | Un solo dueño del token; lo pendiente queda en Postgres si el bot está caído. |
| D-09-02 | Un solo bot de Telegram sirve a todos los usuarios; cada usuario vincula su chat. | Un bot por usuario | Telegram lo permite; menos tokens, menos procesos. |
| D-09-03 | Cuentas y terceros se referencian **por id**; el nombre es libre. Los cruces desde fuentes externas usan campos estructurados (`last4_cuenta`, `last4_tarjeta`, `phone`). | Cruzar por nombre | Andrés: "trabajar por id en todo el proyecto para no tener hardcode". |

## Etapas
| Etapa | Qué | Estado | Spec |
|---|---|---|---|
| A/B | MVP Telegram: texto + voz → borrador → confirmación | ✅ en producción | `docs/bot_ia.md` |
| C | Bandeja web de borradores | ✅ | `docs/bot_ia.md` |
| E / E.2 / E.3 | Fotos como evidencia (cero inferencia), ubicación, múltiples evidencias, botones inline | ✅ 09-sep-2026 | `docs/checkpoints.md` 2026-09-08/09 |
| B.5 | RAG semántico (pgvector) | ⏳ requiere aprobación | — |
| D | WhatsApp (Meta Cloud API) | ⏳ requiere dominio + TLS | — |
| **F** | **SMS de Bancolombia → borradores automáticos** | 🔵 EN CURSO (22-sep-2026) | [09.F-sms-bancolombia.md](09.F-sms-bancolombia.md) |
| G | Completar tercero y concepto desde Telegram; cuentas bancarias de terceros | PLANIFICADO | [09.G-completar-borrador.md](09.G-completar-borrador.md) |
| H | OCR de comprobantes con botón dedicado (Gemini Flash) + trabajo lento fuera del poller | PLANIFICADO | [09.H-ocr-comprobantes.md](09.H-ocr-comprobantes.md) |

> La antigua "F — Consultas/comandos de lectura" de `docs/bot_ia.md` §9 la cubre el módulo 13 (Análisis Inteligente, hito 3). Se reasigna la letra para no dejar huecos.
