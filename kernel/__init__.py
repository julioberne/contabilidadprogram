# -*- coding: utf-8 -*-
"""
kernel/__init__.py — FIN-SYS OS v2.0 Kernel
=============================================
El Kernel es el corazón del ERP. Contiene las funciones básicas que
toda empresa necesita: motor contable (partida doble), bus de eventos,
y funciones compartidas entre módulos.

Componentes:
  - kernel_accounting  → Motor de partida doble (Debe = Haber)
  - kernel_event_bus   → Pub/sub interno para desacoplar módulos

Uso:
  from kernel.kernel_accounting import registrar_asiento
  from kernel.kernel_event_bus import emit, on
"""
