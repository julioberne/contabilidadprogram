# 📕 PRD — FIN-SYS OS (Product Requirements Document)

> **Versión**: 2.0 · **Fecha**: 2026-07-29 · **Dueño de producto**: Andrés (FIN-SYS)
>
> **Qué es este documento**: la fuente de verdad de la **intención de negocio**. Define qué es
> el producto, cómo debe sentirse y bajo qué reglas opera — independiente de cómo esté
> implementado hoy. El código sigue al PRD, nunca al revés: si el código contradice este
> documento, el código está mal o este documento necesita una decisión explícita del dueño.
>
> **Qué NO es**: no es documentación técnica. Nada de rutas de archivos, endpoints, tablas,
> puertos ni credenciales. El mapa técnico vive en `api_spec.md`, `database_schema.md`,
> `architecture_design.md` y `AGENTS.md`; la versión machine-readable para agentes de prueba
> (TestSprite) se regenera desde el código en `testsprite_tests/standard_prd.json`.

---

## 1. Visión

FIN-SYS OS es el **sistema operativo financiero y de gestión de una persona que dirige varios
negocios a la vez**. Reemplaza el caos de hojas de cálculo, chats y papeles con un solo lugar
donde conviven la contabilidad real de cada negocio, la estructura del holding y la operación
del equipo humano.

No es un ERP corporativo genérico: es un **panel de mando personal**. Su usuario arquetípico es
el dueño-operador que lo mismo registra un gasto desde el celular por voz, revisa si un negocio
sigue solvente, aprueba un movimiento de una empresa del holding, o consulta cuánto se le ha
pagado a un empleado y qué documentos tiene firmados.

**La promesa central**: *"todo lo que es verdad sobre mi dinero y mis equipos está aquí, está
al día, y puedo confiar en ello."*

## 2. Sentimiento del producto (identidad)

La app debe *sentirse* como una **terminal de operaciones**, no como una app de consumo:

- **Honestidad brutal**: los datos se muestran crudos, densos y sin decoración. Números antes
  que ilustraciones. Si algo está mal (insolvencia, deuda, dato incompleto), se grita en
  pantalla — nunca se suaviza ni se esconde.
- **Estética retro-brutalista**: alto contraste, tipografía monoespaciada, bordes duros,
  cero degradados amables. La interfaz comunica seriedad y control, como un instrumento
  profesional. Cada territorio tiene identidad propia: la contabilidad vive en blanco/negro
  con acentos de estado; la torre de control del holding tiene su propia identidad ámbar/dorada
  que no se mezcla con lo demás.
- **Velocidad de operador**: los flujos frecuentes (registrar una transacción, mover una tarea,
  consultar un saldo) deben resolverse en segundos y con el mínimo de pasos. La densidad de
  información es una virtud, no un defecto.
- **Control absoluto del humano**: la automatización (voz, IA) propone; el humano dispone.
  Nada entra a los registros oficiales sin confirmación humana.
- **Idioma**: la experiencia completa es en español. Los términos contables usan la convención
  colombiana (IVA, GMF, NIT, cédula).

## 3. Principios de producto (no negociables)

1. **La verdad contable es sagrada.** Un registro confirmado en el libro diario es un hecho.
   Nada lo altera silenciosamente; toda corrección es visible y auditable.
2. **Toda transacción tiene responsable fiscal.** No existe movimiento confirmado sin un
   tercero identificado (NIT o cédula). La única excepción son los borradores pendientes de
   revisión, que se marcan de forma inconfundible como incompletos.
3. **Borrador primero.** Cualquier entrada generada por IA (voz, texto natural) nace como
   borrador. El usuario la confirma con un gesto explícito o la corrige antes de que toque el
   libro oficial.
4. **Los impuestos se calculan solos y siempre igual.** El IVA (19%) y el GMF (4×1000) son
   reglas del negocio, no opciones del usuario: al activarlos, el sistema calcula; el usuario
   nunca hace la aritmética fiscal a mano.
5. **El dinero sale de una cuenta concreta.** Todo movimiento nuevo se ancla a una cuenta
   real del usuario. El sistema advierte cuando una operación excede los fondos disponibles.
   Las cuentas de crédito pueden quedar en negativo: eso es deuda, no un error.
6. **Los módulos no se rompen entre sí.** Agregar o cambiar una capacidad jamás puede degradar
   otra. Cada dominio (contabilidad, holding, equipo humano) es un territorio con frontera
   clara; comparten identidad y sesión, no fragilidad.
7. **Un solo login, una sola identidad.** El usuario entra una vez y toda la casa se abre según
   su rol. No hay segundos logins internos ni cuentas paralelas por módulo.
8. **Los secretos nunca viven en documentos ni en pantalla.** Credenciales y llaves solo
   existen en configuración privada. Ningún mensaje de error revela cómo entrar.
9. **Lo destructivo exige rango y intención.** Reiniciar datos, sembrar datos de prueba o
   apagar módulos son actos de administrador, protegidos y con confirmación explícita. Jamás
   están al alcance de un click casual o de un usuario sin rango.
10. **La documentación acompaña cada hito.** Un cambio de alcance, regla o limitación no está
    terminado hasta que este PRD y los documentos técnicos lo reflejen.

## 4. Quién usa el sistema (roles)

| Rol | Quién es | Qué puede |
|---|---|---|
| **Administrador (dueño-operador)** | El dueño del sistema y de los negocios | Todo: operar todos los módulos, administrar usuarios y roles, encender/apagar módulos, ver consolas de administración, ejecutar acciones destructivas |
| **Miembro** | Colaborador con acceso | Operar los módulos habilitados y ver la información de su ámbito; no ve salarios ni historiales ajenos, no administra el sistema |
| **Empleado de roster** | Persona gestionada (sin acceso) | No entra al sistema; existe como ficha: perfil laboral, pagos, documentos, tareas asignadas |

Reglas de acceso que importan al negocio:
- El rango se define centralmente y los módulos lo heredan; subir o bajar a alguien es una
  acción del administrador en un solo lugar, con efecto inmediato en toda la app.
- Un usuario sin rango que intenta llegar a una zona administrativa simplemente no la
  encuentra: el sistema lo devuelve a su inicio.
- Cada quien puede cambiar su propia contraseña demostrando conocer la actual; una contraseña
  nueva tiene un mínimo de seguridad exigido.
- La sesión sobrevive a un refresco de página, y cerrar sesión limpia todo rastro local.

## 5. El dominio (lenguaje del negocio)

Conceptos que todo el equipo — humano o IA — debe usar con el mismo significado:

**Territorio contable**
- **Portafolio**: la esfera de primer nivel que separa universos de dinero (cada negocio, y la
  vida personal, son portafolios distintos). Nada se mezcla entre portafolios.
- **Transacción**: el átomo del sistema. Ingreso o egreso con monto, concepto, fecha, cuenta de
  origen, tercero responsable, y opcionalmente impuestos, etiquetas, evidencia (comprobante) y
  efectos derivados (cartera, activos).
- **Libro Diario**: la vista canónica de todas las transacciones; se puede buscar, filtrar,
  auditar y revisar la evidencia de cada fila. Sus totales son la verdad.
- **Tercero**: persona o empresa fiscal con la que se transacciona. Se crea una vez y se
  reutiliza; el sistema combate los duplicados.
- **Cuenta**: bolsillo real de dinero (banco, efectivo, tarjeta) con moneda y saldo vivo.
- **Cartera**: lo que me deben (CxC) y lo que debo (CxP), con vencimientos y abonos.
- **Activo**: bien patrimonial que nace de una compra y se rastrea con valor propio.
- **Caja Viva**: el semáforo de solvencia del portafolio activo — nominal, en advertencia o
  insolvente — siempre visible mientras se opera, con alertas de riesgo explícitas.

**Territorio del holding**
- **Entidad**: nodo del árbol corporativo (holding → empresa → sub-entidad → proyecto). Cada
  entidad consolida indicadores propios y de sus hijos.
- **Aprobación**: solicitud de decisión que espera el visto bueno de quien tiene rango.
- **Recurso/ID legal**: documento o identificador oficial (NIT, cámaras, contratos) inventariado
  por entidad.
- **Colaborador de entidad**: persona con permisos sobre una rama del árbol.

**Territorio del equipo**
- **Workspace**: espacio de trabajo de un equipo; contiene proyectos, tareas, notas, calendario
  y miembros.
- **Tarea**: unidad de trabajo con responsable, estado y fechas; se vive en tablero kanban o
  lista.
- **Ficha de empleado**: perfil laboral completo — datos de RRHH, salario e historial de pagos,
  documentos, historial de eventos y vínculo con empresas.

⚠️ **Decisión vigente**: el mundo de "empresas" de RRHH (vínculos laborales) y el árbol de
entidades del holding son **universos separados a propósito**. Unificarlos requiere decisión
explícita del dueño de producto; ningún agente debe "arreglarlo" por iniciativa propia.

## 6. Reglas de negocio por área

**Contabilidad**
1. Registrar una transacción exige: monto válido, concepto, cuenta de origen y tercero. El
   formulario rechaza envíos incompletos con error visible.
2. Activar IVA muestra el impuesto calculado antes de confirmar; el total refleja base +
   impuestos sin intervención manual.
3. El GMF se aplica según la regla colombiana vigente (4×1000) cuando corresponde.
4. Una compra puede, en el mismo gesto, crear el activo que compra y/o abrir una posición de
   cartera (a crédito) — el usuario no repite datos.
5. La evidencia (comprobante) es adjuntable y consultable por transacción; solo se aceptan
   formatos de imagen/documento seguros.
6. El selector de empresa/portafolio cambia TODO el contexto: dashboard, libro, cartera,
   activos y saldos muestran solo el universo elegido.

**Entrada por voz (IA)**
7. La voz produce una transcripción y una propuesta estructurada; si falta el tercero u otro
   dato obligatorio, el borrador queda marcado como incompleto y no puede confirmarse hasta
   completarse.
8. Confirmar un borrador completo es un solo gesto; corregirlo abre el formulario ya
   pre-llenado.

**Holding (torre de control)**
9. Crear una entidad exige ubicarla en el árbol (quién es su padre); eliminarla exige rango y
   nunca elimina silenciosamente ramas con contenido.
10. Los indicadores de una entidad consolidan su rama completa; volver a la raíz muestra el
    consolidado del holding.
11. Las aprobaciones pendientes son visibles y no se resuelven solas: alguien con rango las
    aprueba o rechaza, y queda rastro de quién.

**Equipo (RRHH / proyectos)**
12. Toda tarea vive en un proyecto de un workspace; cambiar su estado la mueve de columna al
    instante y para todos.
13. El salario y el historial de pagos de una persona son visibles solo para administradores.
14. Los documentos de un empleado se organizan en carpetas con categorías configurables; subir,
    previsualizar y descargar nunca alteran el original.
15. Las notas y el calendario pertenecen al workspace: lo que un miembro registra, el equipo lo
    ve según sus permisos.

**Sistema**
16. Los módulos se pueden encender/apagar en caliente por el administrador; el menú y el
    launchpad reflejan el cambio de inmediato, sin redeploy. El inicio (home) jamás puede
    apagarse.
17. Los módulos anunciados pero no construidos se muestran como "próximamente" y no llevan a
    ninguna parte rota: llevan al inicio.
18. Toda ruta desconocida aterriza en el inicio; refrescar la página en cualquier vista la
    conserva.

## 7. Capacidades por módulo (alcance actual)

**Activos hoy**: Inicio, Contabilidad, RRHH/Hub de proyectos, Torre de Control, y las zonas de
sistema (administración, usuarios, módulos, cuenta propia).

**Anunciados (próximamente)**: Tesorería, Facturación, Organigrama, Ventas & CRM, Compras,
Logística, Bot IA, Configuración avanzada, Auditoría.

Los viajes de usuario que el producto garantiza hoy:

- **Entrar y orientarse**: login → inicio con launchpad de módulos → estado general de un
  vistazo. Con credenciales malas, error claro; con sesión activa, el refresco no expulsa.
- **Operar la contabilidad**: elegir empresa/portafolio → ver Caja Viva y dashboard → registrar
  transacción (manual o por voz) → verla en el Libro Diario → auditar con filtros, totales y
  evidencia → gestionar terceros, cuentas, etiquetas, impuestos, activos y cartera desde el
  panel contextual.
- **Gobernar el holding**: entrar a la torre → leer KPIs consolidados → navegar el árbol y
  enfocar cualquier entidad → crear/organizar entidades → despachar aprobaciones → consultar
  IDs legales y colaboradores.
- **Dirigir el equipo**: entrar al hub → cambiar de workspace/proyecto → mover tareas en el
  kanban → registrar notas y eventos → consultar el roster → abrir la ficha completa de un
  empleado (perfil, salario, documentos, historial).
- **Administrar el sistema**: consola de administración con estado del sistema y accesos a
  cada área → encender/apagar módulos → gestionar usuarios y roles → mantener la cuenta propia.

## 8. Ciclos de vida que importan

- **Transacción**: (borrador IA →) validación → confirmada en el libro → auditable con
  evidencia. Confirmada = intocable salvo corrección visible.
- **Aprobación**: creada → pendiente (visible para quien decide) → aprobada/rechazada con
  rastro.
- **Tarea**: creada → en progreso → hecha; siempre asignable y re-asignable.
- **Sesión**: login → operación multi-módulo con una sola identidad → logout limpio (o
  expiración de los permisos sensibles con el tiempo).
- **Módulo**: anunciado → activo ↔ apagado (por flag) → nunca "roto a medias" en el menú.

## 9. Calidad: cómo se ve el éxito

El sistema está sano cuando, verificado de extremo a extremo:

1. Un usuario real puede completar cada viaje del §7 sin ayuda ni conocimiento técnico.
2. Los cálculos fiscales dan siempre el resultado normativo (la verificación canónica: sobre
   $100.000 → IVA $19.000, GMF $400).
3. Ninguna acción de un módulo degrada a otro (principio Zero-Impact verificable).
4. Los datos que se ven son los datos que hay: totales del libro = suma real; KPIs = estado
   real de la rama; semáforo de caja = solvencia real.
5. Las pruebas autónomas (agentes tipo TestSprite) pueden recorrer los viajes del §7 contra
   este PRD **bajo reglas de respeto a los datos reales**: jamás disparar acciones
   destructivas, jamás borrar registros existentes, marcar todo dato de prueba con un prefijo
   identificable, y dejar la configuración (flags, roles, contraseñas) como estaba.

## 10. Fuera de alcance / anti-metas

- No es multi-tenant comercial: es la casa de un operador y su equipo, no un SaaS.
- No busca parecer "amigable": la densidad y el tono de terminal son identidad, no deuda de UX.
- La IA no toma decisiones contables ni aprueba nada: propone y espera al humano.
- No se unifican los universos de empresa (RRHH vs holding) sin decisión del dueño.
- Nada de features nuevas que exijan romper la frontera de un módulo existente.

## 11. Limitaciones asumidas (estado honesto)

- Varios módulos del launchpad son anuncios de intención, no capacidades (ver §7).
- La facturación dentro de contabilidad es un esqueleto visual sin comportamiento.
- El acceso de lectura general no exige credenciales reforzadas; solo los actos destructivos
  están blindados. Endurecerlo es deuda aceptada, no un bug.
- Quien no es administrador no recibe un "acceso denegado" explícito en zonas admin: se le
  redirige al inicio en silencio. Decisión estética vigente, revisable.
- Existen registros contables históricos anteriores a la regla de cuenta obligatoria; se
  toleran como legado documentado.

## 12. Glosario mínimo

- **Caja Viva** — semáforo de solvencia en tiempo real del portafolio activo.
- **Cartera** — cuentas por cobrar (CxC) y por pagar (CxP).
- **GMF** — Gravamen a los Movimientos Financieros (4×1000, Colombia).
- **Holding** — el conjunto de empresas y proyectos del dueño, visto como árbol.
- **Launchpad** — la parrilla de módulos del inicio.
- **Portafolio** — universo contable independiente (un negocio, o la vida personal).
- **Roster** — la nómina de personas gestionadas, tengan o no acceso al sistema.
- **Tercero** — contraparte fiscal (NIT/cédula) de una transacción.
- **Zero-Impact** — principio: lo nuevo jamás degrada lo existente.
