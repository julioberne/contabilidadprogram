"""Simula MacroDroid: manda SMS reales de Bancolombia al webhook (etapa 09.F).

Sin dependencias (urllib). Envía las 3 muestras reales del 21-sep-2026, un SMS
no reconocido y la primera muestra repetida (debe responder DUPLICADO).
En ≤ 45 s el poller (fin_sys_core/bot_telegram.py) los convierte en borradores
y los manda al chat vinculado.

Uso:  .venv\\Scripts\\python.exe scripts\\sms_simular.py --token TOKEN [--url http://localhost:8000/api/webhooks/sms] [--form]
      --form manda application/x-www-form-urlencoded (lo que usa MacroDroid); por defecto JSON.
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

MUESTRAS = [
    ("85540", "Bancolombia: Transferiste $11,900.00 desde tu cuenta *3037 a la cuenta *3193301184 "
              "el 21/09/26 a las 20:00. ¿Dudas? Llamanos al 018000931987. Estamos cerca."),
    ("85540", "Bancolombia: Transferiste $2,500.00 desde tu cuenta *3037 a la cuenta *3114452993 "
              "el 21/09/26 a las 21:44. ¿Dudas? Llamanos al 018000931987. Estamos cerca."),
    ("85540", "Bancolombia: Transferiste $4,530,000 desde tu cuenta *3037 a la cuenta *91232656625 "
              "el 21/09/2026 a las 17:24. ¿Dudas? Llamanos al 018000931987. Estamos cerca."),
    ("85540", "Bancolombia: Compraste $45,000.00 en EXITO con tu T.Deb *7706 el 21/09/26 a las 12:10. "
              "(familia sin muestra real: debe caer en NO RECONOCIDO)"),
]


def enviar(url, token, remitente, texto, form=False):
    if form:
        data = urllib.parse.urlencode({"from": remitente, "text": texto}).encode()
        ctype = "application/x-www-form-urlencoded"
    else:
        data = json.dumps({"from": remitente, "text": texto}, ensure_ascii=False).encode("utf-8")
        ctype = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": ctype, "X-SMS-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--url", default="http://localhost:8000/api/webhooks/sms")
    ap.add_argument("--form", action="store_true")
    a = ap.parse_args()

    ok = True
    envios = MUESTRAS + [MUESTRAS[0]]          # la última es el duplicado
    for i, (rem, texto) in enumerate(envios, 1):
        status, cuerpo = enviar(a.url, a.token, rem, texto, a.form)
        esperado = "DUPLICADO" if i == len(envios) else "ACEPTADO"
        marca = "OK " if (status == 202 and esperado in cuerpo) else "!! "
        ok = ok and marca == "OK "
        print(f"{marca}[{i}] HTTP {status} {cuerpo[:80]}  ← {texto[:48]}…")

    status, cuerpo = enviar(a.url, "token-malo", "85540", MUESTRAS[0][1], a.form)
    print(f"{'OK ' if status == 401 else '!! '}[token inválido] HTTP {status}")
    status, cuerpo = enviar(a.url, a.token, "1234", MUESTRAS[0][1], a.form)
    print(f"{'OK ' if status == 403 else '!! '}[remitente no permitido] HTTP {status}")
    status, cuerpo = enviar(a.url, a.token, "85540", "x" * 5000, a.form)
    print(f"{'OK ' if status == 413 else '!! '}[cuerpo > 4 KB] HTTP {status}")
    ok = ok and status == 413

    print("\nAhora mira Telegram: en ≤ 45 s deben llegar 4 borradores (uno ⚠️ no reconocido)."
          if ok else "\nAlgo no cuadró: revisa el server (¿migración corrida? ¿token vigente?).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
