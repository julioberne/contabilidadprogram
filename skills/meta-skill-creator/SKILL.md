---
name: meta-skill-creator
description: Skill diseñada específicamente para guiar a los agentes en la creación, refinamiento y empaquetado de habilidades contables y financieras personalizadas para el proyecto FIN-SYS OS.
---

# 🛠️ Meta-Skill Creator - Constructor de Habilidades de FIN-SYS OS

Esta habilidad proporciona las instrucciones, estándares y plantillas para que cualquier agente de Antigravity pueda crear y documentar habilidades de negocio personalizadas dentro de este proyecto.

---

## 1. Reglas de Estructura de una Skill
Toda skill generada para FIN-SYS OS debe seguir esta estructura exacta de archivos dentro de su directorio:

```
[nombre-de-la-skill]/
 ├── SKILL.md            <-- (Requerido) Metadatos en YAML e instrucciones de dominio
 ├── scripts/            <-- (Opcional) Scripts automatizados en Python (ej. validadores contables)
 ├── examples/           <-- (Opcional) Ejemplos de uso del código o JSONs de prueba
 └── references/         <-- (Opcional) Leyes, fórmulas fiscales u hojas de cálculo de referencia
```

---

## 2. Plantilla Obligatoria para `SKILL.md`
Cuando generes una nueva skill, debes utilizar la siguiente cabecera con YAML frontmatter y secciones:

```markdown
---
name: [nombre-de-la-skill]
description: [breve-descripcion-de-una-linea]
---

# 📑 [Nombre Completo de la Skill]

## 1. Propósito y Alcance
[Explica qué conocimientos o automatizaciones otorga esta habilidad]

## 2. Reglas del Dominio
[Enlista las reglas matemáticas, contables o técnicas específicas]

## 3. Scripts de Verificación
[Cómo ejecutar las herramientas y scripts dentro de la carpeta scripts/]

## 4. Ejemplos Prácticos
[Ejemplos de comandos o código]
```

---

## 3. Flujo para crear la Skill `contabilidad-helper`
Cuando el usuario apruebe iniciar el desarrollo de la lógica matemática de contabilidad:
1. Lee los requisitos del módulo de impuestos local (ej. IVA 19% en Colombia, GMF 4x1000).
2. Crea la carpeta `skills/contabilidad-helper/`.
3. Escribe el archivo `SKILL.md` documentando las fórmulas exactas.
4. Escribe un script en Python `skills/contabilidad-helper/scripts/validate_accounting.py` que compruebe la partida doble (débito == crédito) en un archivo JSON de asientos contables.
