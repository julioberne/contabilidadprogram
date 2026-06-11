# Patrones del Sistema — FIN-SYS OS v2.0

> Este archivo documenta las decisiones de arquitectura tomadas y los patrones de diseño adoptados.
> NO cambiar estos patrones sin discusión explícita.

---

## Decisiones Arquitectónicas Clave

### 1. Arquitectura Desacoplada en 3 Capas
**Decisión**: Separar estrictamente lógica de negocio, API y UI.
- `fin_sys_core/` → Python puro. Sin imports de FastAPI ni de red.
- `server.py` → Solo enruta y valida con Pydantic. Cero lógica de negocio.
- `frontend/src/` → Solo visualiza. Cero cálculos financieros.

**Por qué**: Permite testear el núcleo matemático sin levantar servidores. Facilita el reemplazo de la UI o la API sin tocar la lógica.

### 2. Zero-Impact Policy para Módulos Nuevos
**Decisión**: Cada módulo nuevo vive en archivos/carpetas nuevas.
- Nuevos endpoints → bloque separado al final de `server.py`
- Nueva UI → nueva carpeta en `frontend/src/` (ej: `control-tower/`, `trading/`)
- Nuevas tablas BD → CREATE TABLE nuevas, nunca ALTER TABLE en tablas existentes
- Nuevo driver → nuevo archivo en `fin_sys_core/` (ej: `control_tower_driver.py`)

**Por qué**: Elimina el riesgo de regresiones en módulos ya funcionales.

### 3. Bandeja de Borradores para IA
**Decisión**: La IA nunca escribe directamente al libro contable oficial.
- Voz → JSON → estado `BORRADOR` → revisión humana → `COMPLETO`
- Los borradores se muestran en ámbar con indicadores de campos faltantes

**Por qué**: El error de IA tiene impacto cero en datos contables reales.

### 4. Árbol Recursivo con CTE para Control Tower
**Decisión**: La tabla `entities` usa auto-referencia (`parent_id`) y los KPIs se calculan con CTE recursivo.
- Un solo query consolida toda la jerarquía descendiente de una entidad
- El árbol puede crecer hasta N niveles sin cambiar el schema

**Por qué**: Flexibilidad máxima sin complejidad adicional en el frontend.

### 5. IDs de Cuentas Fijos (1–7)
**Decisión**: Los IDs de `user_accounts` en Supabase son fijos y el frontend los conoce.
- Al reiniciar la BD, se usa `RESTART IDENTITY CASCADE` + re-seed con IDs explícitos
- La secuencia se fija con `SELECT setval('user_accounts_id_seq', 7)`

**Por qué**: Evita el problema de FK mismatch cuando se reinicia la BD en desarrollo.

---

## Patrones de Código

### Backend (FastAPI)
```python
# Patrón: función en fin_sys_core/ → llamada limpia desde server.py
# NO hacer esto en server.py:
result = psycopg2.connect(...).execute(...)  # ❌

# SÍ hacer esto:
from fin_sys_core.database_driver import registrar_transaccion
result = registrar_transaccion(tx_data)  # ✅
```

### Frontend (React)
```jsx
// Patrón: estado local por componente, fetch con useEffect
// No usar Context API ni Redux — el proyecto no lo requiere aún

// Patrón: edición inline con doble clic
onDoubleClick={() => setEditingCell({row: id, col: field})}
onKeyDown={(e) => e.key === 'Enter' && guardarEdicion()}
```

### Control Tower (Módulo 07)
```jsx
// Patrón: estado global del CT en un solo hook
const { session, entities, kpis, approvals } = useControlTower();
// No mezclar estado del CT con estado de App.jsx
```

---

## Convenciones de Nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos Python | snake_case | `tax_motor.py`, `database_driver.py` |
| Archivos React | PascalCase | `ControlTowerApp.jsx`, `CTKpiCards.jsx` |
| Endpoints API | kebab-case | `/api/ct/quick-transaction` |
| Tablas BD | snake_case | `workspace_users`, `entity_members` |
| Variables JS | camelCase | `portfolioName`, `entityId` |
| Constantes | UPPER_SNAKE | `IS_POSTGRES_ACTIVE`, `GROQ_API_KEY` |

---

## Restricciones Conocidas (No Cambiar Sin Discusión)

1. **No usar React Router** — navegación manual en `main.jsx` es intencional (evita complejidad innecesaria)
2. **No usar ORM** — `psycopg2` directo es suficiente y más predecible para contabilidad
3. **No usar Redux / Zustand** — estado local es suficiente por ahora; CT usa hook propio
4. **No floating point en contabilidad** — todos los cálculos usan `DECIMAL(15,2)` en BD y Python native float solo para visualización
5. **No JWT en demo** — `workspace_users` usa MD5 para demo local; migrar a bcrypt+JWT antes de producción
