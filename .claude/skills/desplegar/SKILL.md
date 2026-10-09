---
name: desplegar
description: Prepara la publicación del trabajo de la sesión en FIN-SYS y la verifica después de que Andrés publica con scripts\publicar.cmd. Antes revisa lo que publicar.cmd no puede juzgar (hito verificado, migraciones, variables nuevas, si hace falta deploy); después sondea lo nuevo en producción y deja el frente y la spec al día. Claude nunca hace push ni corre publicar.cmd.
disable-model-invocation: true
---

# Desplegar (preparar y verificar la publicación)

Reparto: **Claude prepara y verifica; Andrés publica.** `scripts\publicar.cmd` (push + CI + deploy + `:8000` + sonda de `/api/health`) lo corre Andrés en su terminal; la guardia te bloquea el push y `publicar.*`.
No dupliques lo que ya hace `publicar.py`: revisar que la rama esté al día y limpia, pedir la aprobación, esperar el CI, desplegar y sondear `/api/health`.

## A. Antes de publicar

1. **Rama al día:** `git fetch -q origin`; si `origin/master` avanzó, `git rebase origin/master` (pasa el clasificador; merge no). Si hay conflictos, detente y explícalos.
2. **Qué se publica:** `git log --oneline origin/master..HEAD` y `git diff --stat origin/master..HEAD`.
3. **Hito verificado** (si no lo hizo `/cerrar-hito` en este mismo estado del código):
   - `python scripts/lint_critico.py` → sin errores graves.
   - Subagente `corredor-tests`: tests del área tocada + tests puros del CI (lista en `.github/workflows/ci.yml`); si se tocó `frontend/`, también `npm run build`. Nada que escriba en la BD sin autorización de Andrés.
   - Si esta publicación CIERRA una etapa de `docs/specs/` (su Estado pasará a HECHA) y no se auditó ya: subagente `auditor-spec` con la spec y los archivos tocados (una vez por etapa: cuesta ~200k tokens). Si el veredicto no es "LISTA PARA HECHA" o "SOLO FALTA LO MANUAL", dilo antes de seguir.
4. **Riesgos que `publicar.cmd` no ve:**
   - ¿Hay `scripts/migrate_*.py` o cambios de esquema? → Andrés corre la migración (antes o después del deploy, según el caso): escríbele el comando exacto.
   - ¿Cambió `.env.production.example` o se lee una variable nueva (`os.environ`, `import.meta.env`)? → Andrés debe crearla en Dokploy antes del deploy.
   - ¿Cambió `docker-compose.yml`, `Dockerfile`, `frontend/nginx.conf` o `requirements.txt`? → deploy de más riesgo: avísalo.
5. **¿Hace falta deploy?** Si los commits solo tocan `docs/`, `tests/`, `scripts/claude_kit/`, `.claude/`, `.github/` o `*.md`, alcanza con `--sin-deploy`. Si tocan `fin_sys_core/`, `routers/`, `kernel/`, `shared/`, `server.py`, `frontend/` (código, html o nginx), compose, Dockerfile o requirements, hace falta deploy completo.
6. **Sonda específica:** define cómo se comprueba en producción lo nuevo, no solo la salud: una ruta nueva sin sesión → 401 (antes 404); una página nueva → 200; un dato visible en la web; un comportamiento del bot que Andrés prueba en su chat.
7. **Frente:** "Pendiente de publicar: <commits>" y el próximo paso.
8. **Mensaje a Andrés** (máximo 10 líneas): qué se publica en una frase por commit, riesgos del paso 4, la sonda, y el comando exacto en un bloque aparte:
   `scripts\publicar.cmd` o `scripts\publicar.cmd --sin-deploy` (para ver antes qué haría: `--simular`). Termina con: «cuando termine, dime "listo"».

## B. Cuando Andrés dice "listo" (o pega la salida de publicar.cmd)

1. **¿Llegó a master?** `git fetch -q origin` y `git merge-base --is-ancestor <último commit> origin/master`.
2. **Si `publicar.cmd` falló**, diagnostica sin volver a publicar:
   - CI en rojo: `gh run list --limit 3` y `gh run view <id> --log-failed`; arregla, commitea y vuelve al punto A.
   - Deploy fallido: revisa el mensaje; solo si Andrés lo pide, `.venv\Scripts\python.exe scratch\deploy_prod.py` + sonda.
3. **Sonda específica** del paso A.6 contra `https://finsys-andres.duckdns.org`, solo lecturas (GET, sin datos de prueba en la BD de producción). Lo que exige una prueba humana (chat, Excel, celular), pídeselo a Andrés en una línea.
4. **Deja constancia:** frente con "En producción: <sha> (fecha)"; en la spec, marca solo los `CA-` comprobados (los MANUAL, cuando Andrés confirme) y el `Estado`; `CHECKLIST.md` si cambió el estado de un módulo. Commitea esos docs (`docs: … en producción`); se publican en la próxima vuelta con `--sin-deploy`.
5. **Mensaje final** (máximo 6 líneas): qué quedó en producción, qué sonda pasó, qué falta probar a mano.
