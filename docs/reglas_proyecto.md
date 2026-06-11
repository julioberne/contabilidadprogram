# 📋 Reglas del Proyecto — FIN-SYS OS v2.0

> **Última actualización**: 09 Junio 2026
> Este documento define las reglas de oro obligatorias para todo agente, subagente y desarrollador que trabaje en este proyecto.

---

## 🥇 Regla 1: Colaboración Paso a Paso con el Usuario

- **Toda estrategia y código se explica en español al usuario antes de ejecutarse.**
- No se realizan cambios estructurales complejos sin aprobación explícita previa.
- Comunicación: profesional, humilde, clara y siempre en español.

---

## 🛡️ Regla 2: Zero-Impact Policy (No Romper lo Existente)

Esta es la regla más importante del módulo Control Tower y aplica a todos los módulos nuevos:

- **NUNCA modificar archivos existentes de forma destructiva.**
- Los módulos nuevos se crean en nuevas rutas, nuevos archivos, nuevas tablas.
- Ejemplos aplicados:
  - Control Tower → `/api/ct/*` (nuevos endpoints en bloque separado en `server.py`)
  - Control Tower UI → `/frontend/src/control-tower/` (carpeta aislada)
  - Control Tower BD → 5 tablas nuevas (`workspace_users`, `entities`, etc.) sin tocar las existentes
  - Navegación → botón adicional en `main.jsx`, no reemplazar el existente

---

## 💻 Regla 3: Arquitectura Desacoplada

- **Capa Python Puro (`fin_sys_core/`)**: Toda la lógica matemática y de negocio vive aquí. Sin dependencias de FastAPI ni red.
  - `tax_motor.py` — Cálculo de impuestos
  - `ledger_math.py` — Caja Viva y Pockets
  - `database_driver.py` — Conexión y CRUD principal
  - `control_tower_driver.py` — Conexión y CRUD del Control Tower
  - `ai_engine.py` — Integración IA (Gemini/Groq)
  - `test_core.py` — Suite de pruebas automáticas (siempre debe pasar 5/5)
- **`server.py`**: Solo enruta, no contiene lógica de negocio.
- **`frontend/`**: Solo visualiza, no calcula.

---

## 🎨 Regla 4: Estética Retro-Brutalista (Módulo Principal)

La interfaz de los módulos 1–6 se rige por:
- Bordes: `2px solid #000000` (negro puro)
- Esquinas: `border-radius: 0px` (cuadradas absolutas)
- Sin sombras suaves ni gradientes difusos; solo sombras 3D duras (`box-shadow: 3px 3px 0 #000`)
- Tipografía: `IBM Plex Mono` monospaced para todo el texto
- Paleta base: negro, blanco, verde HSL para estados positivos, ámbar `#FFB000` para advertencias

## 🟡 Regla 4b: Estética Control Tower (Módulo 07)

El Control Tower tiene su propia identidad visual independiente:
- **Color de acento exclusivo**: Ámbar/dorado (`#fbbf24`, clase Tailwind `amber-400`)
- Fondo negro (`bg-black`)
- Bordes ámbar (no negro)
- Sombras duras en ámbar: `shadow-[8px_8px_0px_#fbbf24]`
- Esta paleta NO se mezcla con el módulo principal

---

## 📊 Regla 5: Integridad de Datos Contables

- **Ninguna transacción se registra en el Libro Diario sin un Tercero válido** (NIT o CC), excepto borradores de voz.
- Las cuentas de crédito pueden tener balance negativo — es comportamiento esperado.
- El campo `account_id` es obligatorio en nuevas transacciones (las legacy sin `account_id` son deuda técnica documentada).
- En producción se usa Supabase PostgreSQL. El modo simulación (`mock_db.json`) solo para desarrollo sin red.

---

## 🤖 Regla 6: Control y Aislamiento de la IA — "Bandeja de Borradores"

- **Ninguna transacción de voz ingresa automáticamente al libro contable oficial.**
- El flujo obligatorio es: Voz → Transcripción → Estructuración → Estado `BORRADOR` → Revisión Humana → Confirmación.
- Los borradores se muestran con indicador ámbar `[BORRADOR: FALTA NIT]` en la interfaz.
- El usuario puede: confirmar con 1 click (si está completo) o abrir el formulario auto-llenado para corregir.

---

## 🔐 Regla 7: Seguridad y Credenciales

- Las credenciales (DB_PASSWORD, API_KEYS) van **exclusivamente en el archivo `.env`** de la raíz.
- El archivo `.env` **NO se commitea** al repositorio.
- El `walkthrough.md` puede mostrar la estructura del `.env` pero no los valores reales.
- Los `workspace_users` del CT usan hashing MD5 para demo local. En producción migrar a bcrypt + JWT.

---

## 🏥 Regla 8: Health Check al Inicio de Sesión

Al iniciar una nueva sesión de trabajo con el agente, **siempre ejecutar primero**:

```bash
python scripts/health_check.py
```

Esto verifica:
1. ✅ Frontend (Vite) respondiendo en `:5173`
2. ✅ Backend (FastAPI) respondiendo en `:8000`
3. ✅ PostgreSQL (Supabase) conectado
4. ✅ Motor matemático (`tax_motor.py`) con cálculos correctos
5. ✅ Control Tower (`/api/ct/entities`) respondiendo

Si algún check falla, reiniciar el servicio correspondiente antes de continuar.

---

## 📁 Regla 9: Organización de Archivos

```
contabilidadprogram/
├── server.py              ✅ No crear server2.py / server_v2.py. Un solo servidor.
├── fin_sys_core/          ✅ Solo módulos Python puros (sin FastAPI)
├── frontend/src/
│   ├── App.jsx            ✅ Módulos 1-6. No agregar módulo CT aquí.
│   └── control-tower/     ✅ Módulo 07 aislado. No mezclar con App.jsx.
├── docs/                  ✅ Documentación actualizada (NO archivos de diseño temporales)
├── scripts/               ✅ Scripts de utilidad permanentes
├── scratch/               🟡 Scripts temporales de prueba (limpiar periódicamente)
└── uploads/               ✅ Evidencias de comprobantes subidos
```

**No crear** archivos como: `server_backup.py`, `App_old.jsx`, `test_temp.py` en la raíz del proyecto.

---

## 🔄 Regla 10: Ciclo de Actualización de Documentación

Cada vez que se completa un hito significativo, actualizar:
1. `docs/checkpoints.md` — nuevo hito con fecha y archivos creados
2. `docs/user_stories.md` — marcar historias como ✅ COMPLETO
3. `docs/database_schema.md` — si se crearon tablas nuevas
4. `docs/api_spec.md` — si se crearon endpoints nuevos
5. `docs/implementaciones_futuras.md` — mover módulo de PLANIFICADO a COMPLETO
