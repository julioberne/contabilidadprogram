# TestSprite — Reporte de Pruebas E2E (MCP)

> **Adenda 2026-07-29 (post-análisis):** los 4 fallos marcados abajo se verificaron contra el
> código y, cuando aplicaba, en vivo con un navegador real. Un hallazgo (Control Tower KPIs) fue
> **descartado como falso positivo** — el hook sí carga los KPIs; se comprobó reproduciendo el
> flujo. Los otros 3 eran reales: 2 ya están corregidos y verificados en vivo
> (`routers/cartera.py`, `CarteraKpiBar.jsx`, `TercerosTab.jsx`, `ContextPanel.jsx`); el
> restante (resumen de empresas en $0) resultó ser un problema de datos de producción, no de
> código — ver el gap #1 actualizado en la sección 4.

---

## 1️⃣ Document Metadata

- **Proyecto:** contabilidadprogram (FIN-SYS OS v2.0)
- **Fecha de ejecución:** 2026-07-29
- **Preparado por:** TestSprite AI + Claude (análisis verificado contra el código)
- **Entorno:** build de producción del frontend servido por FastAPI en un solo origen (túnel TestSprite); login `andres@finsys.os` (rol owner)
- **Alcance:** 30 de 50 casos del plan (tope del modo producción); prioridad alta primero
- **Resultado global:** ✅ **25 pasaron · ❌ 5 fallaron (83.33%)**
- **Datos creados por las pruebas (prefijo `TS-TEST-`):** 2 transacciones "TS-TEST-Ingreso automatizado" ($250.000 y $100.000) y 1 tarea RRHH "TS-TEST-Prepare monthly review". Los flags de módulos quedaron restaurados (bot re-habilitado).

---

## 2️⃣ Requirement Validation Summary

### R1 — Login global
> El usuario entra con email y contraseña; credenciales malas producen error claro.

| Test | Resultado | Detalle |
|---|---|---|
| TC001 Sign in to the authenticated shell ([código](./TC001_Sign_in_to_the_authenticated_shell.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/2cb61f6f-d5b8-48e5-bf97-f8cd9a451049)) | ✅ | Login correcto entra al shell con sidebar y launchpad |
| TC015 Reject invalid login credentials ([código](./TC015_Reject_invalid_login_credentials.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/620222fc-6092-43c5-9034-d1328de5065e)) | ✅ | Credenciales inválidas muestran el error esperado sin filtrar información |

### R2 — Persistencia de sesión y logout

| Test | Resultado | Detalle |
|---|---|---|
| TC004 Keep the signed-in shell after reload ([código](./TC004_Keep_the_signed_in_shell_after_reload.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/02b7ef52-04d5-4e53-9347-bef5c1c4fffc)) | ✅ | La sesión sobrevive al refresco |
| TC005 Log out from the global header ([código](./TC005_Log_out_from_the_global_header.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/ff15f70c-d047-4615-9267-47036b12795d)) | ✅ | Logout limpia la sesión y vuelve al login |

### R3 — Navegación del shell y deep links

| Test | Resultado | Detalle |
|---|---|---|
| TC008 Switch between enabled modules from the sidebar ([código](./TC008_Switch_between_enabled_modules_from_the_sidebar.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/3d6cdf61-3162-473a-83ac-824cd3b82b46)) | ✅ | Cambio entre Contabilidad / RRHH / Tower con URL sincronizada |
| TC010 Open Contabilidad from the home launchpad ([código](./TC010_Open_Contabilidad_from_the_home_launchpad.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/aab9a6df-4c75-4496-a44b-46ab9c5891f8)) | ✅ | Launchpad → módulo con URL correcta |
| TC012 Open Contabilidad directly and keep it on reload ([código](./TC012_Open_Contabilidad_directly_and_keep_it_on_reload.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/8fda88ed-8a54-4c40-aa0d-18bea500161a)) | ✅ | Deep link + F5 conservan la vista |

### R4 — Contabilidad: registro de transacciones

| Test | Resultado | Detalle |
|---|---|---|
| TC002 Create and review a transaction in Libro Diario ([código](./TC002_Create_and_review_a_transaction_in_Libro_Diario.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/68778b11-85b0-435b-b363-576310f62e9e)) | ✅ | Transacción creada y visible en el libro |
| TC003 Create a transaction and see it in the ledger ([código](./TC003_Create_a_transaction_and_see_it_in_the_ledger.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/ee578aa1-31b7-4853-b1b2-85f0bad6bc33)) | ❌ | **Causa raíz real (no era de refresco)**: `DashboardPanel.jsx` pide `/api/dashboard-data?portfolio=<entity.name>` — busca el portafolio **por nombre**, usando el nombre de la entidad del Control Tower como si fuera el nombre del portafolio contable. Verificado en BD: ninguna entidad de Control Tower (`Mi Holding Principal`, `CONSTRUCTORA BLU SAS`, …) tiene su columna `portfolio_id` poblada, y sus nombres no coinciden con ningún registro de `portfolios` (`Negocio A`, `MI EMPRESA`, `Negocio Principal`, …). El resumen consolidado nunca puede encontrar coincidencia, sin importar cuántas transacciones se registren. No es un bug de código de bajo riesgo — es un vacío de datos entre dos catálogos que requiere una decisión del dueño del producto sobre qué entidad mapea a qué portafolio (ver gap #1). |

### R5 — Contabilidad: empresa, portafolio y dashboard

| Test | Resultado | Detalle |
|---|---|---|
| TC013 Select a portfolio and see its dashboard context update ([código](./TC013_Select_a_portfolio_and_see_its_dashboard_context_update.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/f2921759-1b22-4935-a704-b89f761de516)) | ✅ | El cambio de portafolio actualiza el contexto |
| TC020 Switch the accounting portfolio context ([código](./TC020_Switch_the_accounting_portfolio_context.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/3cc306f2-9eb4-4486-8a98-a90243a29e92)) | ✅ | Contexto contable aislado por portafolio |

### R6 — Contabilidad: Libro Diario

| Test | Resultado | Detalle |
|---|---|---|
| TC022 Search transactions in Libro Diario ([código](./TC022_Search_transactions_in_Libro_Diario.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/adb10f67-bff2-427c-b461-a2454eef56b3)) | ❌ | **Feature inexistente**: el Libro Diario no tiene campo de búsqueda/filtro (verificado en el código: no existe ningún input de búsqueda en la vista del libro; el único "Buscar" es el de terceros). No es una regresión — es una brecha entre la expectativa del plan y la UI real. Decidir: agregar buscador (recomendado) o ajustar la especificación. |
| TC024 Review ledger entries from the accounting context tabs ([código](./TC024_Review_ledger_entries_from_the_accounting_context_tabs.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/5025713f-c63e-4968-9065-32b29b8e0423)) | ✅ | Entradas del libro consultables desde el panel |
| TC028 Review ledger totals ([código](./TC028_Review_ledger_totals.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/a5aee8b8-138d-4e48-a3dd-d18ba7831247)) | ✅ | Totales del libro renderizados |

### R7 — Contabilidad: panel contextual (7 tabs)

| Test | Resultado | Detalle |
|---|---|---|
| TC016 Switch accounting context tabs ([código](./TC016_Switch_accounting_context_tabs.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/ba80c9af-fcb4-493c-8e41-307e8c361f4f)) | ✅ | Las 7 pestañas renderizan su contenido |
| TC021 Review cartera KPI bar and ledger rows ([código](./TC021_Review_cartera_KPI_bar_and_ledger_rows.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/2e9a1778-173d-4f10-9355-1b57da4ecd77)) | ✅ Corregido | **Causa raíz real**: `GET /api/cartera/summary` nunca devolvió los campos que `CarteraKpiBar.jsx` esperaba (`cxc_total`, `cxp_total`, `vencido_total`, `proximo_total`) — el backend usaba otros nombres (`pendiente_cxc`, `pendiente_cxp`) y ni siquiera calculaba vencido/próximo a vencer. **Fix aplicado**: [routers/cartera.py](../routers/cartera.py) ahora agrega esos 4 campos al summary (montos reales de cartera pendiente, vencida y próxima a vencer ≤7 días), de forma aditiva sin romper los consumidores existentes; [CarteraKpiBar.jsx](../frontend/src/contabilidad-v2/components/cartera/CarteraKpiBar.jsx) además gana un fallback a 0 como defensa. Verificado: `GET /api/cartera/summary` ahora devuelve `"cxc_total":0.0,...` en vez de campos ausentes. |
| TC025 Create a third party in accounting ([código](./TC025_Create_a_third_party_in_accounting.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/1c61e986-f9be-4d21-9b8b-e2d89642c889)) | ✅ Corregido | **UI engañosa (confirmado)**: la sección "O crear nuevo:" de la pestaña Terceros tenía los campos pero no tenía botón de guardar ni llamada de creación. **Fix aplicado**: se agregó el botón "✓ Crear Tercero" en [TercerosTab.jsx](../frontend/src/contabilidad-v2/components/tabs/TercerosTab.jsx), que llama `POST /api/third-parties` (endpoint ya existente en `routers/cartera.py`) vía un nuevo helper `createItem` en [ContextPanel.jsx](../frontend/src/contabilidad-v2/components/ContextPanel.jsx), con manejo de error inline y sin tocar el borrador de la transacción en curso. Verificado en vivo: se creó y listó "TS-TEST-Verificacion Fix" con éxito (luego eliminado de la BD por ser solo de verificación). |

### R8 — RRHH / Project Hub

| Test | Resultado | Detalle |
|---|---|---|
| TC006 Switch RRHH workspace and project ([código](./TC006_Switch_RRHH_workspace_and_project.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/95df00fa-c57f-497a-941b-c01833892df7)) | ✅ | Cambio de workspace y proyecto |
| TC014 Create a new RRHH task ([código](./TC014_Create_a_new_RRHH_task.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/8309c42e-5b1b-4c75-aed8-8b96080584c8)) | ✅ | Tarea creada (quedó "TS-TEST-Prepare monthly review" en estado todo) |
| TC017 Manage RRHH tasks in the board view ([código](./TC017_Manage_RRHH_tasks_in_the_board_view.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/43963eb8-3821-4983-8f09-ca444eb6b642)) | ✅ | Gestión de tareas en el tablero |
| TC029 Open the member list and view a member profile ([código](./TC029_Open_the_member_list_and_view_a_member_profile.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/891f4e37-9ae3-4c28-b923-1bbf78a32658)) | ✅ | Roster y ficha de miembro |

### R9 — Control Tower

| Test | Resultado | Detalle |
|---|---|---|
| TC007 Inspect Control Tower hierarchy and KPI cards ([código](./TC007_Inspect_Control_Tower_hierarchy_and_KPI_cards.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/7f9df4c5-574a-4260-9b19-7fff42a73fe0)) | ✅ | Jerarquía y cards presentes |
| TC009 Inspect the control tower entity tree and KPI cards ([código](./TC009_Inspect_the_control_tower_entity_tree_and_KPI_cards.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/75e1ad95-b130-4633-a9a1-3f42a0ccde8b)) | ✅ | Árbol de entidades navegable |
| TC019 View the Control Tower KPI overview ([código](./TC019_View_the_Control_Tower_KPI_overview.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/22829b47-4064-469a-8ec9-45844c6f675f)) | ⚠️ Falso positivo | **Descartado tras verificación en vivo.** `useControlTower.js` sí tiene un `useEffect` (línea 136) que llama `fetchKpis(activeEntity.id)` cada vez que cambia la entidad activa, y el endpoint `/api/ct/entities/{id}/kpis` responde 200 con datos reales. Reproducido en navegador: al seleccionar "Mi Holding Principal" las 5 cards muestran "CAJA DISPONIBLE $0", "SUB-ENTIDADES 2 hija(s)", etc. — los valores son $0 porque el holding no tiene transacciones vinculadas (dato, no bug), no porque no carguen. El agente de TestSprite probablemente no esperó lo suficiente al fetch async antes de inspeccionar el DOM. |
| TC023 Select a child entity in the Control Tower tree ([código](./TC023_Select_a_child_entity_in_the_Control_Tower_tree.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/dcd639b2-11f1-43d6-8842-547ffde4dbba)) | ✅ | Selección de entidad hija con breadcrumb |
| TC027 Review approvals, resources, and collaborators ([código](./TC027_Review_approvals_resources_and_collaborators_in_Control_Tower.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/923b6190-67d3-466b-90c6-1e3b52ac1c8e)) | ✅ | Modales de aprobaciones, recursos y colaboradores |

### R10 — Feature flags de módulos

| Test | Resultado | Detalle |
|---|---|---|
| TC018 Disable a module and see navigation update ([código](./TC018_Disable_a_module_and_see_navigation_update.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/979f458a-f814-49a1-8c34-104f5a797e21)) | ✅ | Toggle refleja el cambio; el módulo quedó re-habilitado al final (verificado en BD) |
| TC026 See the module feature flags list ([código](./TC026_See_the_module_feature_flags_list.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/d82e61d3-649d-45fc-8123-7a8bd6463563)) | ✅ | Lista de flags renderizada |

### R11 — Administración y usuarios

| Test | Resultado | Detalle |
|---|---|---|
| TC011 Open the admin console as owner ([código](./TC011_Open_the_admin_console_as_owner.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/24176589-f01c-4654-bd35-9fda796ef469)) | ✅ | Panel de administración accesible para owner |
| TC030 Review the system user table ([código](./TC030_Review_the_system_user_table.py) · [dashboard](https://www.testsprite.com/dashboard/mcp/tests/cd3134cd-ac73-4da6-9f0e-2bb17061093c/7913eac3-bbd7-48da-a8bd-715557f45fab)) | ✅ | Tabla de usuarios del sistema |

---

## 3️⃣ Coverage & Matching Metrics

- **83.33% de los tests ejecutados pasaron** (25/30). Se ejecutaron los 30 de mayor prioridad de un plan de 50 (tope del modo producción).

| Requisito | Tests | ✅ Pasaron | ❌ Fallaron |
|---|---|---|---|
| R1 Login global | 2 | 2 | 0 |
| R2 Sesión y logout | 2 | 2 | 0 |
| R3 Navegación y deep links | 3 | 3 | 0 |
| R4 Registro de transacciones | 2 | 1 | 1 |
| R5 Empresa/portafolio y dashboard | 2 | 2 | 0 |
| R6 Libro Diario | 3 | 2 | 1 |
| R7 Panel contextual (7 tabs) | 3 | 1 | 2 |
| R8 RRHH / Project Hub | 4 | 4 | 0 |
| R9 Control Tower | 5 | 4 | 1 |
| R10 Feature flags | 2 | 2 | 0 |
| R11 Administración y usuarios | 2 | 2 | 0 |
| **Total** | **30** | **25** | **5** |

No ejecutados por el tope de 30: TC031–TC050 (perfiles de miembro en detalle, notas/calendario, IVA en formulario, mi-cuenta, aprobaciones/recursos en detalle, etc.).

---

## 4️⃣ Key Gaps / Risks

Ordenados por severidad (análisis verificado contra el código fuente y, cuando aplicaba, en vivo con navegador — no solo contra la observación del agente de TestSprite):

1. **[ALTA — dato de producción, requiere decisión del dueño] El resumen consolidado de empresas siempre muestra $0 en ingresos/gastos** (TC003). Causa raíz real: `DashboardPanel.jsx` busca el portafolio contable **por nombre** (`/api/dashboard-data?portfolio=<nombre-de-la-entidad-CT>`), pero ninguna entidad del Control Tower tiene su `portfolio_id` poblado y sus nombres (`Mi Holding Principal`, `CONSTRUCTORA BLU SAS`...) no coinciden con ningún `portfolios.name` real (`Negocio A`, `MI EMPRESA`, `Negocio Principal`...). No es un bug de refresco — es un vacío de vinculación entre dos catálogos de producción. **No se corrigió automáticamente**: mapear qué entidad corresponde a qué portafolio es una decisión de negocio, no algo que deba inferirse por texto. Pendiente: que el dueño defina la vinculación (llenar `entities.portfolio_id`) o renombre para que coincidan.

2. **[MEDIA — corregido] "O crear nuevo:" en Terceros no creaba nada** (TC025). ✅ Arreglado: botón "Crear Tercero" wired a `POST /api/third-parties`, verificado en vivo.

3. **[MEDIA — corregido] Cartera mostraba "$NaN"** (TC021). ✅ Arreglado: el backend nunca envió los campos que el frontend leía; se agregaron de forma aditiva en `/api/cartera/summary`, más un fallback defensivo en el frontend.

4. **[Descartado] KPIs del Control Tower "sin cargar"** (TC019) — falso positivo del agente de pruebas; el flujo real funciona y fue verificado en navegador. Ver detalle en la fila TC019.

5. **[BAJA — brecha de spec] El Libro Diario no tiene buscador** (TC022). No es regresión: la UI nunca lo tuvo. Decidir si se agrega (recomendado para libros largos) o se retira de la expectativa.

6. **[Observación de backend, fuera de los tests]** La tabla `module_flags` acumula filas duplicadas por módulo en cada toggle (5 filas para `bot`) en vez de hacer upsert. Funciona porque "la última gana", pero conviene normalizar.

7. **Higiene de datos de prueba**: quedaron 2 transacciones `TS-TEST-Ingreso automatizado` ($250.000 y $100.000) y 1 tarea `TS-TEST-Prepare monthly review` en la BD real (el tercero de verificación del fix #2 ya fue eliminado). Todas identificables por el prefijo; eliminarlas es decisión del dueño.

---

## 5️⃣ Correcciones aplicadas en esta sesión

| # | Archivo(s) | Cambio | Verificación |
|---|---|---|---|
| 1 | [routers/cartera.py](../routers/cartera.py) | `GET /api/cartera/summary` ahora también devuelve `cxc_total`, `cxp_total`, `vencido_total`, `proximo_total` (montos reales de cartera pendiente/vencida/próxima a vencer ≤7 días), aditivo sobre el shape existente | `curl /api/cartera/summary` → los 4 campos presentes, sin NaN |
| 2 | [CarteraKpiBar.jsx](../frontend/src/contabilidad-v2/components/cartera/CarteraKpiBar.jsx) | Fallback `Number(k.value \|\| 0)` para nunca mostrar NaN aunque falte un campo | Revisión de código |
| 3 | [ContextPanel.jsx](../frontend/src/contabilidad-v2/components/ContextPanel.jsx) | Nuevo helper `createItem(endpoint, data, refreshFn)` (POST genérico), pasado a `TercerosTab` | Revisión de código |
| 4 | [TercerosTab.jsx](../frontend/src/contabilidad-v2/components/tabs/TercerosTab.jsx) | Botón "✓ Crear Tercero" con estado de carga/error, llama `POST /api/third-parties` sin alterar el borrador de la transacción en curso | Probado en navegador: creación + listado exitoso, registro de prueba luego eliminado |

Bug #1 del análisis original (KPIs de Control Tower) se descartó tras verificación — no requirió cambio de código. Bug #2 original (resumen $0) no se tocó porque su fix real implica una decisión de negocio (vinculación entidad↔portafolio), no un cambio de código de bajo riesgo.

---
