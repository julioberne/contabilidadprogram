# SPEC NN.X — <Título de la etapa>

> **Módulo:** NN <Nombre> · **Nivel:** etapa · **Estado:** PLANIFICADO | EN CURSO | HECHO (DD Mes AAAA)
> **Versión:** 1.0 — DD Mes AAAA · **Depende de:** [NN-slug/SPEC.md](SPEC.md) · **Reglas que aplican:** <números de `docs/reglas_proyecto.md`>
> **Qué NO cubre:** <una línea: lo que alguien podría esperar y queda fuera>

## 1. Objetivo
<Dos o tres frases: qué problema resuelve para el usuario y qué se ve distinto al terminar.>

## 2. Alcance
**Incluye:** <lista corta>
**Excluye:** <lista corta, con la etapa donde sí entra>

## 3. Requisitos
| ID | Requisito | Origen |
|---|---|---|
| R-NNX-01 | <verificable, una frase> | <Andrés DD-mes / Regla N / incidente> |

## 4. Diseño
- **Flujo:** <diagrama ASCII o lista numerada>
- **Datos:** tablas nuevas o columnas nuevas → enlace a `docs/database_schema.md#…`; uso de tablas existentes.
- **Endpoints:** → enlace a `docs/api_spec.md#…` (método, ruta, auth, códigos).
- **Archivos:** tabla CREAR / MODIFICAR con la función o sección que cambia.
- **Seguridad:** auth, secretos, límites (tamaño, tasa), qué se registra.

## 5. Decisiones
| ID | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D-NNX-01 | <qué se decidió> | <qué no> | <razón en una frase> |

## 6. Criterios de aceptación
| ID | Criterio (verificable) | Cómo se verifica | Estado |
|---|---|---|---|
| CA-NNX-01 | <observable> | <test / comando / captura> | ☐ |

## 7. Plan de pruebas
- **Unitarias (CI):** módulos y nombres de test.
- **Integración (local, BD):** módulos `skipUnless`.
- **Manual / E2E:** pasos numerados con comandos en PowerShell 5.1.

## 8. Operación
- **Variables de entorno:** nombre, servicio del compose, default.
- **Migración:** script, orden respecto al deploy, idempotencia.
- **Deploy / rollback:** qué se despliega, cómo se apaga (kill-switch) si algo sale mal.
- **Retención / límites:** qué crece, cuándo se purga.

## 9. Checklist de cierre
- [ ] `CA-` marcados y `Estado: HECHO (fecha)` en la cabecera
- [ ] `CHECKLIST.md` (fila del módulo + comando de tests si cambió)
- [ ] `docs/checkpoints.md` (entrada de la sesión con SHA)
- [ ] `docs/database_schema.md` / `docs/api_spec.md` solo si hubo tablas, columnas o endpoints nuevos
- [ ] `SPEC.md` del módulo: fila de la etapa actualizada
