# 🎨 FIN-SYS OS v2.0 - Sistema de Diseño (Brutalismo Retro-Técnico)

Este sistema de diseño define las pautas visuales, la tipografía, las paletas de colores, el tamaño y las reglas de estilo para la terminal financiera de escritorio **FIN-SYS OS v2.0**. Está inspirado en las interfaces de las computadoras profesionales de los años 80 (IBM/Macintosh Classic) fusionado con el CSS Brutalista moderno.

---

## 1. Tipografía y Alineación de Rejilla

Se utiliza tipografía monospaced para forzar una alineación absoluta de caracteres, creando una estructura altamente técnica y predecible similar a una hoja de cálculo física.

* **Fuente Principal**: `IBM Plex Mono`, monospace.
* **Fuente Secundaria**: `Courier New`, monospace (alternativa).
* **Pesos de Fuente (Weights)**:
  * `400` (Regular) - Datos estándar del libro diario, etiquetas de campos.
  * `500` (Medium) - Texto de botones, cabeceras de pestañas.
  * `700` (Bold) - Números grandes, cabeceras de tablas, títulos principales.
* **Escala de Tamaños**:
  * `h1` (Título de la App): `24px` / `1.5rem` (mayúsculas, negrita).
  * `h2` (Título de Sección): `18px` / `1.125rem` (mayúsculas, negrita).
  * `body` (Estándar): `14px` / `0.875rem`.
  * `small` (Metadatos/Hora): `11px` / `0.6875rem`.

---

## 2. Paleta de Colores (HSL y HEX)

El sistema evita los colores suaves, las sombras degradadas y las transparencias. Cada color es sólido, de alto contraste y tiene un significado funcional.

| Token | HEX | HSL | Significado Semántico |
| :--- | :--- | :--- | :--- |
| **Surface (Fondo)** | `#FCF9F2` | `hsl(43, 41%, 97%)` | Papel blanco hueso (Fondo general de la aplicación) |
| **Console Base** | `#FFFFFF` | `hsl(0, 0%, 100%)` | Blanco puro (Fondo de módulos y campos activos) |
| **Borders & Text** | `#000000` | `hsl(0, 0%, 0%)` | Negro sólido (Líneas de rejilla, contornos gruesos) |
| **System Green** | `#00FF66` | `hsl(144, 100%, 50%)` | Crecimiento, Estado Nominal, Ingreso Activo |
| **System Amber** | `#FFB000` | `hsl(41, 100%, 50%)` | Advertencias, Plazo Medio, Alertas de Gasto |
| **System Crimson**| `#FF3B30` | `hsl(3, 100%, 60%)` | Egreso Activo, Déficit, CXP Urgente |
| **Active Neutral** | `#EBE6D8` | `hsl(43, 23%, 88%)` | Gris-beige (Acciones en hover, pestañas inactivas) |

---

## 3. Reglas de Estructura y Geometría

Cada elemento en FIN-SYS OS sigue una alineación matemática estricta:

* **Bordes**: Siempre sólidos, negros de alto contraste.
  * Paneles principales y botones grandes: `2px solid #000000`
  * Tablas internas, campos dinámicos y líneas divisoras: `1px solid #000000`
* **Radio de Borde (Border Radius)**: Cero absoluto (`border-radius: 0px !important`). Todos los paneles, campos, pestañas y alertas tienen esquinas completamente cuadradas y afiladas.
* **Sombras (Shadows)**: Sin sombras suaves. Solo sombras brutalistas sólidas en 3D para botones interactivos (ej. `box-shadow: 4px 4px 0px #000000;`).
* **Espaciado y Relleno (Padding)**: Basado en una rejilla de `8px`.
  * Padding de tarjetas: `16px`.
  * Altura de fila de tabla: `32px` de altura de línea.

---

## 4. Componentes Interactivos

### A. Pestañas Monospaced (Cambio de Entidad)
Se usa para alternar entre libros diarios activos (ej. Negocio A, Negocio B, Finanzas Personales).
* **Estado Inactivo**: `background: #FCF9F2; border-bottom: 2px solid #000000; border-right: 1px solid #000000;`
* **Estado Activo**: `background: #FFFFFF; border-bottom: none; border-top: 2px solid #000000; border-left: 2px solid #000000; border-right: 2px solid #000000; font-weight: bold;`

### B. Botón de Triple Opción (Ingreso / Gasto / Transferencia)
Define el tipo de operación en el formulario:
* **Ingreso (Verde activo)**: `background: #00FF66; color: #000000;` al seleccionarse.
* **Gasto (Rojo activo)**: `background: #FF3B30; color: #FFFFFF;` al seleccionarse.
* **Transf (Negro activo)**: `background: #000000; color: #FFFFFF;` al seleccionarse.

### C. Campos de Formulario Brutalistas
Campos de texto monospaced con contornos negros gruesos.
```css
input[type="text"], input[type="number"], select {
  font-family: 'IBM Plex Mono', monospace;
  background-color: #FFFFFF;
  border: 2px solid #000000;
  padding: 8px 12px;
  color: #000000;
  border-radius: 0px;
  outline: none;
}
input[type="text"]:focus {
  background-color: #FCF9F2;
  border-color: #00FF66; /* Cambia a verde del sistema al escribir activamente */
}
```

### D. Tarjetas Métricas (Caja Viva)
Tres paneles destacados en la barra superior para mostrar totales acumulados en tiempo real:
* **Total Ingresos**: Fondo verde HSL (`#00FF66`) con texto negro, indicador en negrita: `[$125,000.00]`.
* **Total Gastos**: Texto monospaced grande con subrayado rojo sólido (`#FF3B30`): `$74,500.00`.
* **Balance Neto**: Visualización grande con indicador de alerta ámbar debajo: `$50,500.00`.

---

## 5. Croquis de la Interfaz Visual

```
+---------------------------------------------------------------------------------------------------+
| FIN-SYS_OS_v2.0   [Negocio A] [Negocio B] [Finanzas Familiares]                   BALANCE: $450,230.00 |
+---------------------------------------------------------------------------------------------------+
|  [ $125,000.00 ] TOTAL INGRESOS   |   $74,500.00 TOTAL GASTOS   |   $50,500.00 BALANCE NETO       |
+---------------------+-----------------------------------------------------------------------------+
| [TERMINAL]          | [MÓDULO 02: LIBRO DIARIO INTELIGENTE]                                      |
| [LIBRO DIARIO]      | +-----------+-----------+----------------------+                            |
| [POCKETS]           | | Negocio A | Negocio B | Finanzas Personales  |                            |
| [MERCADO]           | +-----------+-----------+----------------------+                            |
| [ARCHIVO]           | | TIPO  | VALOR   | CONCEPTO        | ID TERCERO   | FECHA    | EVIDENCIA |   |
|                     | +-------+---------+-----------------+--------------+----------+-----------+   |
| [MÓDULO 01]         | | ING   | +$50k   | Fees Asesoría   | 900.120.456- | 01/06/26 | [VER]     |   |
| (Registro Manual)   | | GAS   | -$15k   | Servidores Cloud| 500.001.222- | 01/06/26 | [VER]     |   |
|                     | +-------+---------+-----------------+--------------+----------+-----------+   |
| Importe: $          |                                                                             |
| Concepto: ...       |                                                                             |
| Tercero ID: ...     |                                                                             |
| [ REGISTRAR ]       |                                                                             |
+---------------------+-----------------------------------------------------------------------------+
```
