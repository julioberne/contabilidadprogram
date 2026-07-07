# Patrones del Sistema — FIN-SYS OS v2.0

> Este archivo documenta las decisiones de arquitectura tomadas y los patrones de diseño adoptados.
> NO cambiar estos patrones sin discusión explícita.

---

## Decisiones Arquitectónicas Clave

### 1. Arquitectura Desacoplada en 3 Capas
**Decisión**: Separar estrictamente lógica de negocio, API y UI.
- `fin_sys_core/` → Python puro. Sin imports de FastAPI ni de red.
- `routers/*.py` → Endpoints agrupados por dominio con APIRouter. Cero lógica de negocio.
- `server.py` → Solo bootstrap: CORS, include_router(), lifespan. **103 líneas.**
- `frontend/src/` → Solo visualiza. Cero cálculos financieros.

**Por qué**: Permite testear el núcleo matemático sin levantar servidores. Facilita el reemplazo de la UI o la API sin tocar la lógica.

### 2. Backend: APIRouter por Dominio (Strangler Fig Pattern)
**Decisión**: Migrar endpoints de server.py monolítico a `routers/` con FastAPI APIRouter.
```
server.py (103 ln) → solo bootstrap
routers/contabilidad.py   (28 ep)
routers/control_tower.py  (16 ep)
routers/hub.py             (15 ep)
routers/hr.py              (16 ep)
routers/cartera.py         (8 ep)
routers/zero_coa.py        (4 ep)
routers/org.py             (5 ep)
routers/inventory.py       (7 ep)
shared/helpers.py          → emit_journal_entry, resolve_bank_code
```
**Por qué**: Cada desarrollador trabaja en su dominio sin conflictos de merge. URLs idénticas → cero impacto frontend. Swagger auto-agrupa por tags.

### 3. Frontend: Module Registry (SSOT)
**Decisión**: Un solo archivo `registry/moduleRegistry.js` define TODOS los módulos del ERP.
- Sidebar, HomeDashboard y main.jsx **consumen** del registry
- Agregar módulo nuevo = **1 entrada** en el registry (antes eran 3 archivos)
- Cada módulo define: id, label, icon, group, accent, active, order, component (lazy), wrapStyle, extraProps

**Por qué**: Elimina triplicación de metadata. Patrón usado por SAP Fiori (manifest.json), Odoo (__manifest__.py), ERPNext (hooks.py).

### 4. Frontend: Custom Hooks para Estado de Negocio
**Decisión**: Extraer lógica de estado de App.jsx a hooks reutilizables en `hooks/`.
```
hooks/useTransactionForm.js   40+ estados  ← formulario completo + handleRegister
hooks/useVoiceRecorder.js     5 + 3 refs   ← grabación → transcripción → IA
hooks/useAccounts.js          9 estados    ← CRUD cuentas financieras
hooks/useProfile.js           6 estados    ← perfil de usuario
hooks/useCalculator.js        5 estados    ← calculadora inline
```

**Patrón fetchDataRef** (dependencia circular):
```javascript
// Problema: hooks necesitan fetchData, pero fetchData usa setters de los hooks
// Solución: ref estable que siempre apunta al closure más reciente
const fetchDataRef = useRef(null);
const stableFetchData = useRef((...args) => fetchDataRef.current?.(...args)).current;
// hooks reciben stableFetchData
fetchDataRef.current = fetchData; // se asigna después de definir fetchData
```

**Por qué**: App.jsx pasa de 2,514 → 1,884 líneas (−25%). Los hooks son testables independientemente. Patrón usado por Netflix (micro-hooks), Uber (domain hooks), Airbnb (custom hooks).

### 5. Zero-Impact Policy para Módulos Nuevos
**Decisión**: Cada módulo nuevo vive en archivos/carpetas nuevas.
- Nuevo módulo → 1 entrada en `registry/moduleRegistry.js`
- Nuevos endpoints → nuevo router en `routers/`
- Nuevo driver → nuevo archivo en `fin_sys_core/`
- Nuevas tablas BD → CREATE TABLE nuevas, nunca ALTER TABLE

**Por qué**: Elimina el riesgo de regresiones en módulos ya funcionales.

### 6. Bandeja de Borradores para IA
**Decisión**: La IA nunca escribe directamente al libro contable oficial.
- Voz → JSON → estado `BORRADOR` → revisión humana → `COMPLETO`

**Por qué**: El error de IA tiene impacto cero en datos contables reales.

### 7. Árbol Recursivo con CTE para Control Tower
**Decisión**: La tabla `entities` usa auto-referencia (`parent_id`) y CTE recursivo.

**Por qué**: Flexibilidad máxima sin complejidad adicional en el frontend.

### 8. Lazy Loading por Módulo (Code Splitting)
**Decisión**: Los módulos pesados (App.jsx, ControlTowerApp, ProjectHubApp) se cargan con `lazy(() => import(...))` definido en el Module Registry.

**Por qué**: Reducción de bundle inicial. Solo se carga el módulo activo.

---

## Patrones de Código

### Backend (FastAPI + APIRouter)
```python
# routers/contabilidad.py
from fastapi import APIRouter
router = APIRouter(tags=["Contabilidad"])

@router.post("/api/transactions")
async def create_transaction(tx: TransactionCreate):
    from fin_sys_core.database_driver import registrar_transaccion
    result = registrar_transaccion(tx.dict())
    return result
```

### Frontend (React + Custom Hooks)
```jsx
// App.jsx — orquestación con hooks
const { amount, setAmount, handleRegister } = useTransactionForm({
  activePortfolio, accounts, fetchData: stableFetchData, setDrafts
});

const { isRecording, startRecording, stopRecording } = useVoiceRecorder({
  activePortfolio, setDrafts
});
```

### Module Registry
```javascript
// Agregar módulo = 1 entrada:
{ id: 'bot', label: 'Bot IA', icon: '◉', group: 'OPERACIONES',
  accent: 'green', active: true, order: 11,
  component: lazy(() => import('../bot/BotApp.jsx')),
  wrapStyle: { minHeight: '100%', width: '100%' } },
```

---

### 9. Error Boundaries por Módulo
**Decisión**: Cada módulo lazy-loaded se envuelve en un `<ErrorBoundary>`.
```jsx
// main.jsx — cada módulo aislado
<ErrorBoundary module={mod.label}>
  <Comp {...props} />
</ErrorBoundary>
```
- Si un módulo crashea, solo ESE módulo muestra el fallback
- El Shell, Sidebar y GlobalHeader siguen intactos
- Botón "Reintentar" resetea el error sin recargar la página
- Stack trace visible en `<details>` colapsable (para debugging)

**Por qué**: Patrón estándar en SAP Fiori, Netflix, Uber. Evita que un bug en un módulo tumbe toda la aplicación.

### 10. Tests Frontend con Vitest
**Decisión**: Tests automáticos para hooks con Vitest + React Testing Library.
```bash
npm test          # 22 tests, 3 archivos (hooks)
npm run test:watch  # Modo watch (re-corre al guardar)
```
- Tests en `hooks/__tests__/*.test.js`
- Config en `vite.config.js` → `test: { environment: 'jsdom' }`
- Setup en `src/test-setup.js` (jest-dom matchers)

**Por qué**: Detecta regresiones inmediatamente al modificar hooks. Vitest es nativo de Vite (zero config extra).

---

## Convenciones de Nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos Python | snake_case | `tax_motor.py`, `database_driver.py` |
| Archivos React | PascalCase | `ControlTowerApp.jsx`, `CTKpiCards.jsx` |
| Hooks React | camelCase con `use` | `useTransactionForm.js` |
| Tests React | `*.test.js` en `__tests__/` | `hooks/__tests__/useCalculator.test.js` |
| Routers FastAPI | snake_case | `routers/control_tower.py` |
| Endpoints API | kebab-case | `/api/ct/quick-transaction` |
| Tablas BD | snake_case | `workspace_users`, `entity_members` |
| Variables JS | camelCase | `portfolioName`, `entityId` |
| Constantes | UPPER_SNAKE | `IS_POSTGRES_ACTIVE`, `API_BASE_URL` |

---

## Restricciones Conocidas (No Cambiar Sin Discusión)

1. **No usar React Router** — navegación manual con Module Registry es intencional
2. **No usar ORM** — `psycopg2` directo es más predecible para contabilidad
3. **No usar Redux / Zustand** — custom hooks + estado local es suficiente
4. **No floating point en contabilidad** — `DECIMAL(15,2)` en BD
5. **No JWT en demo** — migrar a bcrypt+JWT antes de producción

---

## Scope Map — Contexto por Módulo (para el agente IA)

> **Regla**: Cuando el usuario mencione un módulo, el agente IA debe leer SOLO los archivos listados.
> Esto reduce el contexto de ~25,000 líneas a ~300-800 líneas por tarea.

| Cuando el usuario dice... | Lee SOLO estos archivos | NO toques |
|---|---|---|
| "Formulario" / "TransactionForm" | `components/TransactionForm.jsx`, `hooks/useTransactionForm.js` | App.jsx, ContextPanel |
| "Cartera" / "CXC" / "CXP" | `components/tabs/CarteraTab.jsx`, `routers/cartera.py` | App.jsx |
| "Libro Diario" / "tabla transacciones" | `components/LibroDiario.jsx` | TransactionForm |
| "Inventario" | `components/inventory/*.jsx`, `routers/inventory.py` | ContextPanel |
| "Panel derecho" / "ContextPanel" | `components/ContextPanel.jsx` + `components/tabs/*.jsx` | App.jsx |
| "Control Tower" | `control-tower/*.jsx`, `hooks/useControlTower.js`, `routers/control_tower.py` | Todo lo demás |
| "RRHH" / "Hub" / "Miembros" | `project-hub/**`, `routers/hub.py`, `routers/hr.py` | Todo lo demás |
| "Documentos" / "archivos" | `project-hub/features/members/tabs/docs/*` | Todo lo demás |
| "Impuestos" / "IVA" | `components/tabs/ImpuestosTab.jsx`, `fin_sys_core/tax_motor.py` | App.jsx |
| "Terceros" | `components/tabs/TercerosTab.jsx` | App.jsx |
| "Evidencia" / "comprobante" | `components/EvidenceModal.jsx` | App.jsx |
| "Voz" / "IA" / "Whisper" | `components/VoiceIngestWidget.jsx`, `hooks/useVoiceRecorder.js`, `fin_sys_core/ai_engine.py` | Todo lo demás |
| "COA" / "PUC" / "cuentas contables" | `components/CoaSelector.jsx`, `hooks/useCoaData.js`, `kernel/`, `routers/coa.py` | App.jsx |
| "Feature Flags" / "Módulos" | `shell/ModuleSettingsPanel.jsx`, `registry/moduleRegistry.js`, `routers/module_flags.py` | Todo lo demás |
| "Shell" / "Sidebar" / "Home" | `shell/*.jsx`, `registry/moduleRegistry.js` | Módulos internos |
| \"Backend contabilidad\" | `routers/transactions.py`, `routers/portfolios.py`, `routers/schemas.py` | Otros routers |
| \"Dashboard\" / \"KPIs\" | `shell/HomeDashboard.jsx`, `components/DashboardPanel.jsx`, `routers/dashboard_data.py` | App.jsx |

### Regla de Archivo Máximo
- **Ningún archivo nuevo debe superar 400 líneas.** Si crece más, dividir de inmediato.
- **1 componente React = 1 archivo .jsx** (para que Vite HMR funcione por módulo).
- **Hooks en archivos .js separados** (no inline en componentes).
