# Contexto Activo — FIN-SYS OS v2.0

> **ACTUALIZAR al inicio Y al final de cada sesión de trabajo con el AI.**
> Este archivo le dice al agente exactamente qué puede y no puede tocar HOY.

---

## Estado: 10 Junio 2026

## Módulo en Construcción
**NINGUNO ACTIVO** — Sistema en estado de mantenimiento/documentación.
Próximo módulo a iniciar: **Módulo 08 — Trading/NASDAQ-100**

---

## Archivos Permitidos en la Próxima Sesión (Módulo 08)
```
server.py                              (solo agregar al FINAL — bloque Trading)
fin_sys_core/trading_driver.py         (NUEVO — crear desde cero)
frontend/src/trading/TradingApp.jsx    (NUEVO — crear desde cero)
frontend/src/trading/hooks/            (NUEVO — carpeta nueva)
frontend/src/trading/components/       (NUEVO — carpeta nueva)
frontend/src/main.jsx                  (solo agregar botón de navegación)
```

## Archivos PROHIBIDOS en la Próxima Sesión
```
frontend/src/App.jsx                   ← NO tocar (módulos 1-6 completos)
frontend/src/control-tower/*           ← NO tocar (módulo 7 completo)
fin_sys_core/database_driver.py        ← NO tocar sin permiso explícito
fin_sys_core/control_tower_driver.py   ← NO tocar sin permiso explícito
fin_sys_core/ai_engine.py              ← NO tocar sin permiso explícito
.env                                   ← NUNCA tocar
Tablas existentes en Supabase          ← NO alterar schema
```

---

## Últimos Cambios (Sesión Anterior — 10 Jun 2026)

### Lo que se hizo:
1. **Limpieza completa de docs/** — 11 archivos eliminados/actualizados para reflejar estado real
2. **Actualización docs/user_stories.md** — 7 módulos completos + 2 planificados, 14 historias
3. **Actualización docs/checkpoints.md** — 12 hitos cronológicos completos
4. **Actualización docs/database_schema.md** — 15 tablas con SQL completo
5. **Actualización docs/api_spec.md** — 18 rutas incluyendo 8 endpoints CT
6. **Actualización docs/architecture_design.md** — diagramas Mermaid con CT y KPI CTE
7. **Creación AGENTS.md** — instrucciones para el agente (NUEVO)
8. **Creación memory-bank/** — memoria persistente del proyecto (NUEVO)
9. **Git inicializado** — .gitignore creado, listo para primer commit

### Archivos modificados:
- docs/ (11 archivos reescritos)
- AGENTS.md (nuevo)
- CHECKLIST.md (actualizado)
- scripts/health_check.py (actualizado con check CT)
- memory-bank/ (nuevo — 4 archivos)
- .gitignore (nuevo)

### Lo que NO se tocó:
- App.jsx, server.py, database_driver.py, control_tower_driver.py
- Ningún archivo de frontend/src/control-tower/
- Ninguna tabla de Supabase

---

## Estado de Salud del Sistema (Verificado 10 Jun 2026)

```
✅ Frontend (React/Vite)  → :5173 OK
✅ Backend (FastAPI)       → :8000 OK
✅ PostgreSQL (Supabase)   → 18 TXs | 7 Entidades CT
✅ Motor Matemático        → IVA=19.000 | GMF=400
✅ Control Tower API       → Balance Holding $42,222,500
```

---

## Deuda Técnica Pendiente (No Bloquea Desarrollo)

| ID | Problema | Impacto | Fix Requerido |
|---|---|---|---|
| DT-01 | Balance Efectivo -$11.2M | Visual (no contable) | UPDATE transactions SET account_id=1 WHERE account_id IS NULL |
| DT-02 | `on_event` deprecation en server.py | Warning en logs | Migrar a `lifespan` handler |
| DT-03 | CT: CXP/CXC en KPIs parcial | KPI "CXC Pendiente" con datos mock | Vincular cxp_cxc_ledger a portafolios del CT |
| DT-04 | MD5 en workspace_users | Solo seguro en demo local | Migrar a bcrypt+JWT antes de producción |

---

## Instrucción de Actualización al Final de Sesión

Al terminar una sesión de trabajo, actualizar este archivo con:
1. Módulo trabajado
2. Archivos que se modificaron
3. Archivos que NO se tocaron
4. Resultado del health check final
5. Nueva deuda técnica descubierta
