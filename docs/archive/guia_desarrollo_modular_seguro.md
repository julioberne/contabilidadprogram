# Guia de Desarrollo Modular Seguro — FIN-SYS OS v2.0
> Basado en mejores practicas 2025 (Anthropic, Cursor, Kiro)
> Adaptado a: Solo fundador → Equipo de 5+

---

## Por que se rompen las cosas — 4 Causas Raiz

| # | Causa | Sintoma |
|---|---|---|
| 1 | Conversacion larga = contexto degradado | El AI olvida reglas, duplica logica o cambia estilos |
| 2 | Sin Git | No hay rollback si algo se rompe |
| 3 | App.jsx gigante (130KB) | Un toque puede afectar cualquiera de los 6 modulos |
| 4 | Sin perimetro definido por sesion | El AI modifica archivos que no deberia tocar |

---

## El Sistema Completo — 5 Capas de Proteccion

```
CAPA 1: AGENTS.md     → Le dice al AI las reglas del proyecto al inicio de cada sesion
CAPA 2: memory-bank/  → Mantiene el estado del proyecto entre sesiones
CAPA 3: Git + Ramas   → Punto de rollback antes de cada cambio riesgoso
CAPA 4: Modulos JSX   → App.jsx dividido en componentes aislados
CAPA 5: Protocolo     → Como pedir cambios sin romper lo demas
```

---

## CAPA 1: AGENTS.md — Instrucciones al AI

Crear en: contabilidadprogram/AGENTS.md

Este archivo es leido automaticamente al inicio de cada sesion. Contiene:
- Stack tecnologico completo
- Tabla de modulos con estado (COMPLETO / EN PROGRESO)
- Zero-Impact Policy: modulos completos no se tocan para features nuevas
- Permisos por archivo (explicito o requiere aprobacion)
- Protocolo pre-cambio: plan → aprobacion → ejecucion
- Comandos de verificacion (health_check.py, test_core.py)
- Paletas de color por modulo (principal vs CT)

---

## CAPA 2: memory-bank/ — Memoria Persistente

Crear: contabilidadprogram/memory-bank/

Archivos:
- projectbrief.md   → Que es el proyecto, para que sirve
- systemPatterns.md → Decisiones de arquitectura tomadas
- activeContext.md  → Modulo actual, archivos permitidos/prohibidos de HOY
- progress.md       → Estado de cada modulo y deuda tecnica conocida

El archivo MAS IMPORTANTE es activeContext.md.
Al inicio de cada sesion, el agente lo lee y sabe exactamente que puede y no puede tocar.
Al final de cada sesion, se actualiza con lo que cambio.

---

## CAPA 3: Git — El Paracaidas (Hacer HOY)

```bash
cd contabilidadprogram
git init
git add .
git commit -m "feat: checkpoint inicial — 7 modulos completos, CT funcional"

# Ramas futuras (crear una por modulo)
git branch modulo-08-trading
git branch modulo-09-bot-whatsapp
```

Flujo obligatorio antes de cada sesion con AI:
```bash
git add -A && git commit -m "checkpoint: antes de [nombre del cambio]"
git checkout -b feature/nombre-del-modulo
```

Si algo se rompe:
```bash
git checkout main   # volver al estado limpio en 1 segundo
```

---

## CAPA 4: Dividir App.jsx (antes de Modulo 08)

Plan de migracion progresiva sin romper nada:

frontend/src/
  App.jsx                     <- Solo el shell y routing (< 200 lineas)
  modules/
    mod01-registro/
      RegistroForm.jsx        <- Formulario principal
      PanelTercero.jsx        <- Panel colapsable de terceros
      PanelImpuestos.jsx      <- Panel IVA, GMF, tasas
      PanelCartera.jsx        <- Panel CXC/CXP
      PanelActivos.jsx        <- Panel activos patrimoniales
    mod02-libro-diario/
      LibroDiario.jsx         <- Tabla + edicion inline
      FilaTransaccion.jsx     <- Fila individual con doble-clic
    mod03-cuentas/
      GestionCuentas.jsx      <- Lista y creacion de cuentas
      PerfilUsuario.jsx       <- Perfil editable
    mod06-voz/
      VoiceSidebar.jsx        <- Microfono + consola + borradores
      BandejaVoz.jsx          <- Lista de borradores
  shared/
    CajaViva.jsx              <- KPI cards del header
    PortfolioTabs.jsx         <- Pestanas de portafolio

Ventaja clave: cuando el AI necesite modificar un panel,
la instruccion es: "Edita SOLO modules/mod01-registro/PanelTercero.jsx. No toques App.jsx."

---

## CAPA 5: Protocolo de Sesion

Plantilla de inicio de sesion (copiar cada vez que se abre una nueva):

  INICIO DE SESION - FIN-SYS OS v2.0
  
  Modulo a trabajar: [NOMBRE]
  Objetivo: [QUE quiero lograr]
  
  ARCHIVOS PERMITIDOS ESTA SESION:
  - [archivo 1]
  - [archivo 2]
  
  ARCHIVOS PROHIBIDOS:
  - App.jsx, database_driver.py, control_tower_driver.py, .env
  
  ANTES DE ESCRIBIR CODIGO:
  1. Muestrame el plan con archivos exactos a tocar
  2. Espera mi confirmacion
  3. Ejecuta un paso a la vez

Senales de alerta — detener la sesion si el AI:
  - Propone modificar App.jsx directamente para un modulo nuevo
  - Sugiere cambiar el schema de tablas existentes
  - Quiere editar database_driver.py sin permiso explicito
  - Propone mas de 3 archivos en un cambio sin plan previo

---

## Plan de Implementacion Priorizado

| Prioridad | Accion | Tiempo |
|---|---|---|
| HOY | git init + primer commit | 5 min |
| HOY | Crear AGENTS.md en la raiz | 10 min |
| HOY | Crear memory-bank/projectbrief.md | 5 min |
| HOY | Crear memory-bank/activeContext.md | 5 min |
| Esta semana | memory-bank/progress.md | 15 min |
| Esta semana | memory-bank/systemPatterns.md | 15 min |
| Antes de Modulo 08 | Dividir App.jsx en modulos JSX | 2-4 h con AI |
| Esta semana | Ramas de Git por modulo futuro | 5 min |

---

## Antes vs. Despues

| Situacion | Antes | Despues |
|---|---|---|
| Inicio de sesion | AI no sabe que ya esta construido | Lee AGENTS.md + activeContext.md automaticamente |
| Cambio en modulo X | Puede afectar modulo Y en App.jsx | Toca solo modules/mod-X/Componente.jsx |
| Algo se rompe | No hay rollback | git checkout main en 1 segundo |
| Nuevo colaborador | No sabe las reglas | Lee AGENTS.md + memory-bank/ y esta al dia |
| Sesion nueva | Se pierde el contexto | activeContext.md captura el estado exacto |

---

## Contexto: Mejores Practicas 2025 que Aplican Aqui

- AGENTS.md / CLAUDE.md: Estandar universal para instrucciones a agentes de AI
- Memory Bank (Cline): Directorio de markdown que persiste contexto entre sesiones
- Git Worktrees: Espacios aislados por feature — un AI por rama sin contaminacion
- Test-First Prompting: Escribir pruebas primero, pedir al AI que las haga pasar
- Spec-Driven Dev (Kiro/AWS): Especificar → revisar plan → ejecutar un paso a la vez
- Perimeter Definition: Siempre decirle al AI que NO puede tocar, no solo que SI

