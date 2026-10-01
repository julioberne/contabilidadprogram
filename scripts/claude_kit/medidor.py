"""Hook UserPromptSubmit del kit de sesión de FIN-SYS (ver docs/guia-trabajo-claude.md).

Cada vez que Andrés envía un mensaje, calcula el contexto actual de la sesión a partir
de la transcripción y, si pasa un umbral suave, le agrega a Claude una línea de aviso
para que proponga cerrar el hito (/cerrar-hito). No bloquea ni corta nada.

Avisa una vez por tramo (por defecto a 350k, 450k, 550k...), no en cada mensaje.
Ajustes por variable de entorno: FINSYS_CTX_AVISO (umbral, tokens) y FINSYS_CTX_PASO (tramo).
Solo actúa dentro de este proyecto. Usa solo la biblioteca estándar y nunca falla hacia afuera.
"""
import json
import os
import sys
import tempfile

PROYECTO = "contabilidadprogram"
UMBRAL = int(os.environ.get("FINSYS_CTX_AVISO", "350000"))
PASO = int(os.environ.get("FINSYS_CTX_PASO", "100000"))
COLA_BYTES = 2_000_000  # se lee solo el final de la transcripción


def contexto_actual(ruta):
    """Tokens de entrada del último turno del asistente (lo que se reenvía en cada turno)."""
    tam = os.path.getsize(ruta)
    with open(ruta, "rb") as fh:
        fh.seek(max(0, tam - COLA_BYTES))
        lineas = fh.read().decode("utf-8", errors="replace").splitlines()
    for linea in reversed(lineas):
        if '"usage"' not in linea:
            continue
        try:
            ev = json.loads(linea)
        except ValueError:
            continue
        if ev.get("type") != "assistant":
            continue
        u = (ev.get("message") or {}).get("usage") or {}
        total = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                 + u.get("cache_creation_input_tokens", 0))
        if total:
            return total
    return 0


def ruta_estado(session_id):
    carpeta = os.path.join(tempfile.gettempdir(), "finsys_medidor")
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, f"{session_id or 'sin-id'}.txt")


def main():
    datos = json.load(sys.stdin)
    cwd = datos.get("cwd") or os.getcwd()
    ruta = datos.get("transcript_path")
    if PROYECTO not in cwd.lower() or not ruta or not os.path.isfile(ruta):
        return
    ctx = contexto_actual(ruta)
    estado = ruta_estado(datos.get("session_id"))
    if ctx < UMBRAL:
        if os.path.exists(estado):
            os.remove(estado)  # tras /clear o compactar, el aviso vuelve a empezar
        return
    tramo = (ctx - UMBRAL) // PASO
    try:
        ultimo = int(open(estado, encoding="utf-8").read().strip())
    except (OSError, ValueError):
        ultimo = -1
    if tramo <= ultimo:
        return
    with open(estado, "w", encoding="utf-8") as fh:
        fh.write(str(tramo))
    aviso = (f"[Medidor FIN-SYS] Contexto actual ~{ctx // 1000}k tokens (aviso desde {UMBRAL // 1000}k). "
             "Cada turno reenvía todo el contexto. Si el hito en curso ya está cerrado y verificado, "
             "díselo a Andrés en una línea y propón /cerrar-hito; si vas a mitad de un hito, sigue sin interrumpir.")
    salida = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": aviso}}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # un hook roto no debe estorbar la sesión
        pass
