# FIN-SYS OS v2.0 — Project Brief

## Propósito
Sistema de contabilidad SaaS para pymes colombianas y contadores B2B/B2C.
Permite registrar transacciones, gestionar multi-empresa (Control Tower) y llevar libros contables con IA de voz.

## Usuarios Objetivo
- **Primario**: Andrés (Fundador) — micro-empresa en crecimiento hacia equipo de 5+
- **Secundario**: Contadores externos, socios inversores, colaboradores asignados por entidad
- **Futuro**: Clientes B2B contratados (empresas que pagan por el servicio de contabilidad)

## Propuesta de Valor
1. Registro contable por voz en español — sin formularios largos
2. Multi-portafolio — gestionar múltiples negocios en una sola interfaz
3. Control Tower — llevar la contabilidad de otras empresas y cobrar por el servicio (B2B)
4. Georreferenciación y auditoría automática de transacciones

## Módulos Completados ✅
- **Módulo 01**: Registro Contable Universal (formulario + paneles colapsables: Tercero, Impuestos, CXC/CXP, Activos)
- **Módulo 02**: Libro Diario Inteligente (tabla multi-portafolio + edición inline estilo Excel)
- **Módulo 03**: Cuentas Multi-Moneda COP/USD + Perfil de Usuario
- **Módulo 04**: Cartera CXC/CXP con fechas de vencimiento
- **Módulo 05**: Activos Patrimoniales con recurrencia
- **Módulo 06**: Motor de Voz (Groq Whisper + Llama 3.3 + RAG pgvector)
- **Módulo 07**: Control Tower — árbol jerárquico, KPIs consolidados, aprobaciones, inventario IDs, colaboradores

## Módulos Planificados 🔵
- **Módulo 08**: Trading/NASDAQ-100 — PnL realizado/flotante integrado a libro contable
- **Módulo 09**: Bot WhatsApp/Telegram — ingestión móvil vía Twilio + Groq
- **Módulo 10**: Reportes PDF/Excel por entidad

## Regla de Oro
**Zero-Impact Policy**: nuevas funcionalidades = nuevos archivos. No destruir lo construido.
