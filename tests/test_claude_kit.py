"""Tests puros del kit de sesión de Claude (scripts/claude_kit/guardia.py y scripts/lint_critico.py).

La guardia es un hook que bloquea acciones peligrosas en TODAS las sesiones: un falso positivo
traba el trabajo diario y un falso negativo deja pasar un push o un SQL contra producción.
Sin BD ni red: solo la función pura `decidir`.
"""
import importlib.util
import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(RAIZ, *ruta.split("/")))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


guardia = _cargar("guardia", "scripts/claude_kit/guardia.py")
lint_critico = _cargar("lint_critico", "scripts/lint_critico.py")
chequeo = _cargar("chequeo_diario", "scripts/claude_kit/chequeo_diario.py")

CWD = r"C:\Users\andre\OneDrive\Escritorio\programas\contabilidadprogram\.claude\worktrees\x"


def bash(comando, herramienta="Bash", cwd=CWD):
    r = guardia.decidir({"cwd": cwd, "tool_name": herramienta, "tool_input": {"command": comando}})
    return r[0] if r else None


def archivo(herramienta, ruta):
    r = guardia.decidir({"cwd": CWD, "tool_name": herramienta, "tool_input": {"file_path": ruta}})
    return r[0] if r else None


class TestGuardiaBloquea(unittest.TestCase):
    def test_push(self):
        self.assertEqual(bash("git push origin claude/x:master"), "deny")
        self.assertEqual(bash('git -C "C:/repo" push'), "deny")
        self.assertEqual(bash("git fetch -q && git push"), "deny")
        self.assertEqual(bash("git push origin x:master", "PowerShell"), "deny")

    def test_publicar(self):
        self.assertEqual(bash(r"scripts\publicar.cmd --sin-deploy", "PowerShell"), "deny")
        self.assertEqual(bash(r'& "C:\repo\scripts\publicar.cmd"', "PowerShell"), "deny")
        self.assertEqual(bash(".venv/Scripts/python.exe scripts/publicar.py --simular"), "deny")

    def test_mantenimiento_sin_check(self):
        self.assertEqual(bash(r".venv\Scripts\python.exe scripts\session_maintenance.py"), "deny")
        self.assertEqual(bash("python scripts/session_maintenance.py --clean"), "deny")

    def test_bot_local(self):
        self.assertEqual(bash("python fin_sys_core/bot_telegram.py"), "deny")
        self.assertEqual(bash("python -m fin_sys_core.bot_telegram"), "deny")

    def test_migraciones(self):
        self.assertEqual(bash(r".venv\Scripts\python.exe scripts\migrate_contadores.py"), "deny")

    def test_sql_de_escritura_contra_la_bd(self):
        self.assertEqual(bash("python - <<'PY'\ncur.execute(\"DELETE FROM transactions WHERE id = 3\")\nPY"), "deny")
        self.assertEqual(bash('psql "$DB" -c "UPDATE accounts SET balance = 0"'), "deny")
        self.assertEqual(bash("python -c \"cur.execute('DROP TABLE x')\""), "deny")

    def test_env(self):
        self.assertEqual(archivo("Read", r"C:\repo\.env"), "deny")
        self.assertEqual(archivo("Edit", "C:/repo/.env"), "deny")
        self.assertEqual(bash("cat .env"), "deny")
        self.assertEqual(bash("Get-Content .env.local", "PowerShell"), "deny")

    def test_dokploy_fuera_del_script(self):
        self.assertEqual(bash('curl -X POST http://159.223.156.50:3000/api/compose.deploy -H "x-api-key: k"'), "deny")

    def test_drivers_piden_permiso(self):
        self.assertEqual(archivo("Edit", r"C:\repo\fin_sys_core\database_driver.py"), "ask")
        self.assertEqual(archivo("Write", "C:/repo/fin_sys_core/control_tower_driver.py"), "ask")


class TestGuardiaDejaPasar(unittest.TestCase):
    """Falsos positivos que trabarían el trabajo diario."""

    def test_git_normal(self):
        for comando in ('git commit -m "docs: falta push"', "git stash push -u -m tag", "git log --oneline -3",
                        "git status --short", "git rebase origin/master", "git -C C:/repo pull --ff-only"):
            self.assertIsNone(bash(comando), comando)

    def test_mensajes_de_commit_que_mencionan_push(self):
        heredoc = ("git add a.py && git commit -q -F - <<'EOF'\nfeat: la guardia niega git push y scripts\\publicar.*\n"
                   "- session_maintenance.py sin --check, bot_telegram.py\nEOF\ngit log --oneline -3")
        self.assertIsNone(bash(heredoc))
        self.assertIsNone(bash('git commit -m "docs: falta git push de Andrés"'))
        ps = "git commit -F - @'\nfix: no git push desde Claude\n'@"
        self.assertIsNone(bash(ps, "PowerShell"))

    def test_heredoc_python_con_sql_sigue_bloqueado(self):
        self.assertEqual(bash("python - <<'PY'\nimport x\ncur.execute(\"UPDATE accounts SET a = 1\")\nPY"), "deny")

    def test_mencionar_no_es_ejecutar(self):
        for comando in ("grep -n publicar.cmd WORKFLOW.md", 'grep -rn "DELETE FROM" fin_sys_core',
                        "grep -n bot_telegram AGENTS.md", 'git grep -n "migrate_" -- scripts',
                        r".venv\Scripts\python.exe scripts\session_maintenance.py --check",
                        "python scratch/deploy_prod.py", "python -c \"cur.execute('SELECT 1')\"",
                        "ls -la .env", 'grep -E "\\.env$"', "python -m unittest tests.test_contadores"):
            self.assertIsNone(bash(comando), comando)

    def test_archivos_normales(self):
        self.assertIsNone(archivo("Edit", r"C:\repo\fin_sys_core\bot_driver.py"))
        self.assertIsNone(archivo("Read", r"C:\repo\fin_sys_core\database_driver.py"))
        self.assertIsNone(archivo("Edit", "C:/repo/.env.production.example"))

    def test_fuera_del_proyecto(self):
        self.assertIsNone(bash("git push", cwd=r"C:\otro\proyecto"))


class TestLintCritico(unittest.TestCase):
    def test_detecta_tests_js(self):
        self.assertTrue(lint_critico.es_test_js("frontend/src/x/__tests__/A.test.jsx"))
        self.assertTrue(lint_critico.es_test_js("frontend/src/utils.spec.js"))
        self.assertFalse(lint_critico.es_test_js("frontend/src/shell/Sidebar.jsx"))

    def test_filtra_solo_errores_graves(self):
        front = os.path.join(RAIZ, "frontend")
        resultados = [
            {"filePath": os.path.join(front, "src", "A.jsx"), "messages": [
                {"severity": 2, "ruleId": "no-unused-vars", "line": 1, "column": 1, "message": "x sin usar"},
                {"severity": 2, "ruleId": "no-undef", "line": 2, "column": 3, "message": "'y' is not defined."},
                {"severity": 1, "ruleId": "no-undef", "line": 3, "column": 1, "message": "aviso"},
                {"severity": 2, "ruleId": None, "fatal": True, "line": 9, "column": 1, "message": "Unexpected token"}]},
            {"filePath": os.path.join(front, "src", "__tests__", "B.test.jsx"), "messages": [
                {"severity": 2, "ruleId": "no-undef", "line": 4, "column": 1, "message": "'global' is not defined."}]},
        ]
        errores = lint_critico.filtrar_eslint(resultados, front)
        self.assertEqual(len(errores), 2)
        self.assertIn("no-undef", errores[0])
        self.assertIn("parseo", errores[1])


def _frontmatter(ruta):
    texto = open(ruta, encoding="utf-8").read()
    cabecera = texto.split("---")[1] if texto.startswith("---") else ""
    campos = {}
    for linea in cabecera.splitlines():
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            campos[clave.strip()] = valor.strip()
    return campos


class TestAgentesYSkills(unittest.TestCase):
    """Un subagente sin `tools` ni `disallowedTools` hereda TODAS las herramientas; sin `model`
    hereda el modelo caro de la sesión. Una skill con efectos debe ser solo del usuario."""

    def test_subagentes_acotados(self):
        carpeta = os.path.join(RAIZ, ".claude", "agents")
        for nombre in sorted(os.listdir(carpeta)):
            campos = _frontmatter(os.path.join(carpeta, nombre))
            self.assertEqual(campos.get("name"), nombre[:-3], nombre)
            self.assertTrue(campos.get("description", "").startswith("Úsalo"), f"{nombre}: la descripción debe decir cuándo actuar")
            self.assertIn(campos.get("model"), ("haiku", "sonnet", "opus"), nombre)
            self.assertTrue(campos.get("tools") or campos.get("disallowedTools"), f"{nombre}: herramientas sin acotar")

    def test_verificador_visual_sin_terminal(self):
        campos = _frontmatter(os.path.join(RAIZ, ".claude", "agents", "verificador-visual.md"))
        for herramienta in ("Bash", "PowerShell", "Edit", "Write"):
            self.assertIn(herramienta, campos.get("disallowedTools", ""))

    def test_auditor_spec_solo_lectura(self):
        campos = _frontmatter(os.path.join(RAIZ, ".claude", "agents", "auditor-spec.md"))
        self.assertEqual(campos.get("tools"), "Read, Grep, Glob")

    def test_desplegar_solo_la_invoca_andres(self):
        campos = _frontmatter(os.path.join(RAIZ, ".claude", "skills", "desplegar", "SKILL.md"))
        self.assertEqual(campos.get("disable-model-invocation"), "true")


class TestChequeoDiario(unittest.TestCase):
    """El tablero lo leen todas las sesiones: sin colores de terminal y jamás con credenciales."""

    SALIDA_HEALTH = ("\x1b[92m✅\x1b[0m [1/7] Frontend OK\n\x1b[91m❌\x1b[0m [2/7] Backend  (FastAPI) → :8000 CAÍDO\n"
                     "\x1b[92m✅\x1b[0m [3/7] PostgreSQL OK\n\x1b[93m⚠️ \x1b[0m 13 transacción(es) sin account_id\n"
                     "\x1b[91m❌\x1b[0m Frontend   (Vite :5173)\n")

    def test_health_sin_ansi_y_con_total_real(self):
        ok, total, problemas = chequeo.resumir_health(self.SALIDA_HEALTH)
        self.assertEqual((ok, total), (2, 3))
        self.assertTrue(problemas)
        self.assertFalse(any("\x1b" in p for p in problemas))

    def test_mantenimiento_no_filtra_credenciales(self):
        salida = ("\x1b[96mCT:   andres@finsys.os / admin123 / API:  http://localhost:8000/docs\x1b[0m\n"
                  "⚠️ 2 workspaces sin nombre\n")
        avisos = chequeo.resumir_mantenimiento(salida)
        self.assertEqual(avisos, ["⚠️ 2 workspaces sin nombre"])
        self.assertFalse(any("admin123" in a for a in avisos))


if __name__ == "__main__":
    unittest.main()
