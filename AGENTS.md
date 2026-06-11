# FIN-SYS OS v2.0 — Instrucciones para el Agente de IA

> Leer este archivo COMPLETO al inicio de cada sesión antes de hacer cualquier cambio.

---

## Stack Tecnológico

| Capa | Tecnología | Archivo / Ruta | Puerto |
|---|---|---|---|
| Backend | FastAPI (Python 3.10+) | `server.py` | `:8000` |
| Frontend | Vite + React | `frontend/src/` | `:5173` |
| Base de Datos | PostgreSQL 17 (Supabase) | Cloud · us-east-2 | — |
| IA Voz | Groq (Whisper + Llama 3.3) | `fin_sys_core/ai_engine.py` | — |
| IA Fallback | Gemini API | `fin_sys_core/ai_engine.py` | — |
| Estilo Visual | Retro-Brutalista | IBM Plex Mono · bordes 2px · 0px radius | — |

---

## Estado de Módulos

| Módulo | Archivos Clave | Estado | Regla |
|---|---|---|---|
| App Principal (01–06) | `frontend/src/App.jsx`, `server.py` | ✅ COMPLETO | NO refactorizar sin permiso |
| fin_sys_core | `database_driver.py`, `tax_motor.py`, `ledger_math.py`, `ai_engine.py` | ✅ ESTABLE | Solo con aprobación explícita |
| Control Tower (07) | `frontend/src/control-tower/*`, `fin_sys_core/control_tower_driver.py` | ✅ COMPLETO | NO mezclar con App.jsx |
| Módulo 08 (Trading) | `frontend/src/trading/*` (por crear) | 🔵 PLANIFICADO | Crear en carpeta nueva |
| Módulo 09 (Bot) | `frontend/src/bot/*` (por crear) | 🔵 PLANIFICADO | Crear en carpeta nueva |

---

## Reglas Críticas — OBLIGATORIAS

### ZERO-IMPACT POLICY
- **NUNCA** modificar archivos de módulos COMPLETOS para agregar funcionalidad nueva
- Módulos nuevos → nuevas rutas, nuevos archivos, nuevas carpetas
- Endpoints nuevos → bloque separado al **final** de `server.py`
- Antes de tocar `App.jsx`, proponer extracción a componente independiente en `frontend/src/modules/`

### PERMISOS EXPLÍCITOS POR ARCHIVO

| Archivo | Permiso |
|---|---|
| `fin_sys_core/database_driver.py` | 🔴 Solo con aprobación explícita del usuario |
| `fin_sys_core/control_tower_driver.py` | 🔴 Solo con aprobación explícita del usuario |
| `server.py` | 🟡 Solo agregar al final. Nunca modificar endpoints existentes |
| `frontend/src/App.jsx` | 🟡 Preferir extraer componente. Nunca reescribir secciones existentes |
| `.env` | 🔴 NUNCA tocar bajo ninguna circunstancia |
| Tablas de BD existentes | 🔴 NUNCA alterar schema sin aprobación explícita |
| `frontend/src/control-tower/*` | 🟡 No mezclar paleta ámbar con paleta brutalista del módulo principal |

### PROTOCOLO OBLIGATORIO ANTES DE CUALQUIER CAMBIO
1. **Listar** exactamente qué archivos se van a modificar y por qué
2. **Mostrar el plan** → **esperar aprobación** del usuario antes de escribir código
3. **Ejecutar un paso a la vez**, no bundling de cambios
4. **Resumir** qué cambió, qué NO se tocó, y qué riesgos existen

---

## Identidad Visual

### Módulo Principal (App 01–06)
- Fuente: `IBM Plex Mono` (monospaced en todo el texto)
- Bordes: `2px solid #000000`
- Border-radius: `0px` — absolutamente cuadrado
- Sombras: `3px 3px 0 #000` — duras, no difusas
- Paleta: negro, blanco, verde HSL (positivo), `#FFB000` ámbar (warnings)

### Control Tower (Módulo 07) — PALETA DIFERENTE, NO MEZCLAR
- Color de acento: ámbar `#fbbf24` (Tailwind `amber-400`)
- Fondo: `bg-black`
- Sombras duras en ámbar: `shadow-[8px_8px_0px_#fbbf24]`
- Esta paleta NO se usa en App.jsx ni viceversa

---

## Comandos de Verificación

```bash
# Ejecutar al INICIO y al FINAL de cada sesión
python scripts/health_check.py

# Tests unitarios del motor matemático (deben pasar 5/5)
python fin_sys_core/test_core.py

# Resultado esperado del health check:
# ✅ Frontend  → :5173 OK
# ✅ Backend   → :8000 OK
# ✅ PostgreSQL → 18 TXs | 7 Entidades CT
# ✅ Motor     → IVA=19.000 | GMF=400
# ✅ CT API    → Balance Holding $42,222,500
```

---

## Arquitectura de Datos (Referencia Rápida)

- **Portafolios activos**: 4 (IDs 1–4: Negocio A, Pegasus, Personal, Principal)
- **Cuentas bancarias**: 7 (IDs 1–7, fijos — no reasignar)
- **Entidades CT**: 7 en árbol de 4 niveles (Holding → Empresa → Sub → Proyecto)
- **workspace_users CT**: 5 (admin: `andres@finsys.os / admin123`)

---

## Contexto de Memoria

> Leer `memory-bank/activeContext.md` para saber en qué módulo se está trabajando HOY
> y cuáles archivos están permitidos/prohibidos en la sesión actual.
