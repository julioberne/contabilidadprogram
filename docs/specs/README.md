# 📐 Specs internos — FIN-SYS OS v2.0

> **Único punto de entrada** a las especificaciones técnicas del proyecto.
> Creado el 22 Sep 2026 (pedido de Andrés: specs "que no se mezclen y estén organizados jerárquicamente").
> El **estado vivo** sigue en `CHECKLIST.md`; la **bitácora** en `docs/checkpoints.md`; las **reglas** en `docs/reglas_proyecto.md`. Un spec nunca duplica esas tres cosas: las enlaza.

## Jerarquía (tres niveles, sin mezclar)

| Nivel | Qué es | Dónde vive | Quién lo cambia y cuándo |
|---|---|---|---|
| **0 — Reglas** | Normas transversales (Zero-Impact, Regla 6 / 6b, seguridad…) | `docs/reglas_proyecto.md` | Solo con aprobación explícita de Andrés |
| **1 — Spec de módulo** | Qué es y qué NO es el módulo, límites, arquitectura, inventario de tablas y endpoints propios (**por enlace**), lista de etapas con estado | `docs/specs/NN-slug/SPEC.md` | Al abrir o cerrar una etapa |
| **2 — Spec de etapa** | Entregable concreto: requisitos, diseño, decisiones, criterios de aceptación verificables, plan de pruebas, operación, checklist de cierre | `docs/specs/NN-slug/NN.X-slug.md` | Se escribe ANTES de implementar; se marca HECHO al cerrar |

Reglas de la jerarquía:
- Un spec de etapa depende de su spec de módulo y cita las reglas por número (`Regla 6b`), nunca las copia.
- El DDL de una tabla y el contrato de un endpoint viven en **un solo lugar**: `docs/database_schema.md` (ancla `### <LETRA>. \`tabla\``) y `docs/api_spec.md` (ancla `### \`MÉTODO /ruta\``). El spec enlaza y, como mucho, resume en una línea.
- `NN` = número de módulo de `CHECKLIST.md` (09 = Bot IA, 12 = Contadores, 13 = Análisis Inteligente…). `X` = letra de etapa (A, B, C…) o número de hito (1, 2, 3) según la convención que ya use ese módulo.
- Identificadores trazables dentro de un spec de etapa: requisitos `R-09F-01`, decisiones `D-09F-01`, criterios de aceptación `CA-09F-01`. Se citan en tests (`# CA-09F-03`) y en mensajes de commit.
- `Estado:` en cabecera: `PLANIFICADO` → `EN CURSO` → `HECHO (fecha)`. Nada más; el detalle del avance va en `CHECKLIST.md`.

## Plantilla

Todo spec nuevo se crea copiando [`_plantilla.md`](_plantilla.md). Un spec de módulo usa las mismas secciones 1–5 y sustituye 6–9 por **"Etapas"** (tabla con estado y enlace a cada spec de etapa).

## Índice

| Módulo | Spec de módulo | Etapas |
|---|---|---|
| 09 Bot IA | [09-bot-ia/SPEC.md](09-bot-ia/SPEC.md) | [09.F SMS Bancolombia](09-bot-ia/09.F-sms-bancolombia.md) · [09.G Completar borrador](09-bot-ia/09.G-completar-borrador.md) · [09.H OCR de comprobantes](09-bot-ia/09.H-ocr-comprobantes.md) |

Módulos sin spec todavía (se crean cuando se abra una etapa nueva sobre ellos): 01–06 Contabilidad (referencia histórica: `docs/D02_FIN_spec.md`, formato anterior), 07 Control Tower, 08 Project Hub / RRHH, 12 Contadores, 13 Análisis Inteligente (plan en `~/.claude/plans/merry-finding-storm.md`).

## Ciclo de vida de un spec de etapa

1. **Diseño**: se escribe el spec (secciones 1–8) y se aprueba con Andrés antes de tocar código.
2. **Implementación**: cada commit cita los `CA-` que cubre. Si una decisión cambia, se edita la sección 5 con la fecha, no se reescribe la historia.
3. **Cierre**: se marcan los `CA-` cumplidos, `Estado: HECHO (fecha)`, y se ejecuta la sección 9 (checklist de cierre: `CHECKLIST.md`, `docs/checkpoints.md`, `database_schema.md` / `api_spec.md` si hubo tablas o endpoints nuevos).

## Deuda conocida de documentación (no se resuelve aquí)

- `docs/reglas_proyecto.md` Regla 10 pide actualizar 5 archivos por hito; `CHECKLIST.md` §"Cierre de sesión" y `WORKFLOW.md` dicen "solo checkpoints + CHECKLIST, nada más". Los specs siguen el criterio de la sección 9 de cada uno (checkpoints + CHECKLIST siempre; schema/api solo si cambiaron).
- `docs/D02_FIN_spec.md` usa una numeración (`D01/D02/D03`) que no existe en ningún otro sitio. Se conserva como referencia histórica; no se migra hasta que se abra una etapa sobre Contabilidad.
- `docs/bot_ia.md` §9 nombraba "F — Consultas/comandos de lectura"; esa capacidad la cubre el módulo 13 (Análisis Inteligente, hito 3). La letra F queda para SMS (ver `09-bot-ia/SPEC.md`).
