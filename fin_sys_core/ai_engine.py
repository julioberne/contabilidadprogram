# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 - Motor de Inteligencia y RAG (ai_engine.py)
------------------------------------------------------------
Este módulo conecta la API de Gemini Multimodal para transcribir y estructurar
transacciones de voz libre en tiempo real, inyectando contexto semántico (RAG)
desde la base de datos PostgreSQL.
"""

import os
import base64
import json
import httpx
from typing import Dict, Any, List, Optional
from database_driver import get_db_connection, obtener_transacciones

# Cliente HTTP reutilizable con timeout (evita abrir/cerrar sockets por request)
_http_client = httpx.Client(timeout=30.0)

# Cargar API Keys desde variables de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL_TRANSCRIPT = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_API_URL_CHAT = "https://api.groq.com/openai/v1/chat/completions"


def get_rag_context(user_voice_concept: str) -> str:
    """
    Busca semánticamente en la base de datos registros históricos o reglas
    de terceros similares al concepto hablado por el usuario.
    
    Si PostgreSQL está apagado, busca en la simulación local en memoria.
    """
    context_examples = []
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Consulta de auditoría rápida para encontrar terceros recurrentes basados en el concepto
        # En producción con pgvector: SELECT ... ORDER BY embedding <=> %s LIMIT 3;
        cur.execute("""
            SELECT t.concept, tp.name, tp.identification_type, tp.identification_number, t.category, t.payment_method
            FROM transactions t
            JOIN third_parties tp ON t.third_party_id = tp.id
            WHERE t.concept ILIKE %s OR t.category ILIKE %s
            ORDER BY t.id DESC
            LIMIT 3;
        """, (f"%{user_voice_concept}%", f"%{user_voice_concept}%"))
        
        rows = cur.fetchall()
        for r in rows:
            ex = (
                f"- Concepto hablado: '{r[0]}' -> Tercero: {r[1]} ({r[2]}: {r[3]}), "
                f"Categoría: {r[4]}, Pago: {r[5]}"
            )
            context_examples.append(ex)
            
    except Exception as e:
        print(f"⚠️ [AVISO RAG] PostgreSQL no activo o error, usando Simulación en Memoria. Detalle: {e}")
        # Intentamos obtener transacciones locales del simulador en memoria
        try:
            txs = obtener_transacciones()
            # Filtrado simple por coincidencia de subcadena (concept o category)
            match_count = 0
            for tx in txs:
                concept_val = tx.get("concept", "") or ""
                cat_val = tx.get("category", "") or ""
                if (user_voice_concept.lower() in concept_val.lower() or 
                    user_voice_concept.lower() in cat_val.lower()):
                    ex = (
                        f"- Concepto hablado: '{concept_val}' -> Tercero: {tx.get('third_party_name', '')} "
                        f"({tx.get('identification_type', 'NIT')}: {tx.get('identification_number', '')}), "
                        f"Categoría: {cat_val}, Pago: {tx.get('payment_method', '')}"
                    )
                    context_examples.append(ex)
                    match_count += 1
                    if match_count >= 3:
                        break
        except Exception as inner_e:
            print(f"⚠️ Error crítico al acceder a transacciones locales: {inner_e}")
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        
    if context_examples:
        return "\nHistorial contable de transacciones similares encontradas:\n" + "\n".join(context_examples)
    return "\nNo hay historial previo para este tipo de concepto. Infiere valores neutrales por defecto."


def transcribe_audio_only(audio_file_path: str) -> str:
    """
    Realiza únicamente la transcripción del audio a texto plano (Speech-to-Text).
    Usa Groq Whisper si la clave está configurada; de lo contrario usa Gemini como fallback.
    """
    if GROQ_API_KEY:
        print("🚀 [GROQ STT] Transcribiendo con Whisper-Large-v3...")
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        mime_type = "audio/wav"
        if audio_file_path.endswith(".webm"):
            mime_type = "audio/webm"
        elif audio_file_path.endswith(".ogg"):
            mime_type = "audio/ogg"

        with open(audio_file_path, "rb") as audio_file:
            files = {"file": (os.path.basename(audio_file_path), audio_file, mime_type)}
            data = {"model": "whisper-large-v3", "language": "es"}
            response = _http_client.post(GROQ_API_URL_TRANSCRIPT, headers=headers, files=files, data=data)

        if response.status_code != 200:
            raise RuntimeError(f"❌ Error en Groq Whisper STT: {response.text}")
        return response.json().get("text", "")

    # Fallback a Gemini si no hay clave de Groq
    if not GEMINI_API_KEY:
        raise ValueError("No se encontraron claves de API para transcribir.")
    
    print("🔄 [FALLBACK GEMINI] Transcribiendo audio multimodal con Gemini...")
    # Leer y codificar el archivo de audio en Base64
    with open(audio_file_path, "rb") as f:
        audio_data = f.read()
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

    mime_type = "audio/wav"
    if audio_file_path.endswith(".webm"):
        mime_type = "audio/webm"
    elif audio_file_path.endswith(".ogg"):
        mime_type = "audio/ogg"

    payload = {
        "contents": [
            {
                "parts": [
                    {"inlineData": {"mimeType": mime_type, "data": audio_b64}},
                    {"text": "Transcribe exactamente lo que se dice en este audio en español. Devuelve solo la transcripción textual y nada más."}
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1}
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    response = _http_client.post(GEMINI_API_URL, headers=headers, params=params, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Error al transcribir con Gemini: {response.text}")
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        raise RuntimeError(f"Fallo al leer respuesta de Gemini: {e}")


def structure_text_only(transcript: str, portfolio_name: str = "Negocio A") -> Dict[str, Any]:
    """
    Toma un texto transcrito de una nota de voz, realiza una búsqueda RAG contable,
    y llama al LLM (Groq Llama 3.3 o Gemini) para estructurarlo en el JSON estricto requerido.
    """
    if not transcript or not transcript.strip():
        raise ValueError("El texto transcrito está vacío.")

    # 1. Obtener contexto RAG
    rag_context = get_rag_context(transcript)

    # 2. Definir las instrucciones y el esquema estricto
    system_instruction = (
        "Eres el asistente inteligente de contabilidad de FIN-SYS OS v2.0.\n"
        "Tu tarea es tomar el texto de una nota de voz contable transcrita, estructurarlo "
        "y extraer los datos financieros en el formato JSON especificado abajo.\n\n"
        "DEBES RETORNAR UN OBJETO JSON CON LA SIGUIENTE ESTRUCTURA EXACTA:\n"
        "{\n"
        "  \"type\": \"INGRESO\" | \"GASTO\" | \"TRANSFERENCIA\",\n"
        "  \"amount\": number, (monto numérico absoluto sin formato de miles o texto)\n"
        "  \"concept\": \"descripción narrativa clara del concepto en mayúsculas de preferencia\",\n"
        "  \"payment_method\": \"Efectivo\" | \"Banco M\" | \"Tarjeta C\" | \"Transferencia\" | null,\n"
        "  \"category\": \"Ventas\" | \"Servicios\" | \"Alimentación\" | \"Suscripciones\" | \"Infraestructura\" | null,\n"
        "  \"third_party\": {\n"
        "    \"identification_type\": \"NIT\" | \"CC\" | null,\n"
        "    \"identification_number\": \"número de identificación sin puntos ni guiones\" | null,\n"
        "    \"name\": \"nombre completo de la persona o empresa\"\n"
        "  },\n"
        "  \"suggested_tags\": [\"etiqueta1\", \"etiqueta2\"],\n"
        "  \"inferred_fields\": [\"campo1\", \"campo2\"]\n"
        "}\n\n"
        "REGLAS DE INFERENCIA CONVERSACIONAL:\n"
        "- Si el usuario no menciona la fecha, asume 'hoy' (calcula la fecha actual en YYYY-MM-DD).\n"
        "- Si el usuario no menciona explícitamente el NIT/cédula o el método de pago, "
        "marca dichos campos como null. No inventes datos ficticios.\n"
        "- Usa el historial contable provisto para autocompletar el NIT si detectas que el tercero coincide "
        "semánticamente con transacciones pasadas.\n"
        "- REGLA MATEMÁTICA: Si la expresión incluye cálculos compuestos o agrupaciones (por ejemplo, "
        "'Gasté en luz 300 mil, agua 200 mil y gas 500 mil por 3 apartamentos' o '13 apartamentos de: 5 a 1.000.000 y 2 a 300.000'), "
        "DEBES calcular internamente el total sumando y multiplicando correctamente. Asigna el total numérico final consolidado al campo `amount`.\n"
        "- Lista en 'inferred_fields' los campos obligatorios que no estaban explícitos y tuviste que inferir.\n"
        f"Contexto RAG de transacciones pasadas:\n{rag_context}"
    )

    # --- RUTA 1: GROQ LLAMA 3.3 ---
    if GROQ_API_KEY:
        print("🚀 [GROQ LLM] Estructurando texto con Llama-3.3-70b...")
        chat_headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        chat_payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Estructura este texto: '{transcript}' para el portafolio '{portfolio_name}'."}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        chat_response = _http_client.post(GROQ_API_URL_CHAT, headers=chat_headers, json=chat_payload)
        if chat_response.status_code != 200:
            raise RuntimeError(f"❌ Error en Groq Llama 3.3: {chat_response.text}")
        chat_result = chat_response.json()["choices"][0]["message"]["content"]
        try:
            parsed_transaction = json.loads(chat_result)
            parsed_transaction["raw_transcript"] = transcript
            return parsed_transaction
        except Exception as e:
            raise RuntimeError(f"❌ Fallo al parsear la respuesta JSON de Llama 3.3: {e}. Respuesta: {chat_result}")

    # --- RUTA 2: GEMINI API (FALLBACK TEXT-TO-JSON) ---
    if not GEMINI_API_KEY:
        raise ValueError("No se configuró ninguna clave de API para procesar el estructurado (Groq o Gemini).")
    
    print("🔄 [FALLBACK GEMINI] Estructurando texto con Gemini 2.5 Flash...")
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "type": {"type": "STRING", "description": "INGRESO, GASTO o TRANSFERENCIA"},
            "amount": {"type": "NUMBER", "description": "Monto numérico absoluto"},
            "concept": {"type": "STRING", "description": "Descripción clara del concepto"},
            "payment_method": {"type": "STRING", "description": "Efectivo, Banco M, Tarjeta C, o Transferencia, o null"},
            "category": {"type": "STRING", "description": "Categoría contable o null"},
            "third_party": {
                "type": "OBJECT",
                "properties": {
                    "identification_type": {"type": "STRING", "description": "CC o NIT"},
                    "identification_number": {"type": "STRING", "description": "Número tributario"},
                    "name": {"type": "STRING"}
                },
                "required": ["name"]
            },
            "suggested_tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "inferred_fields": {"type": "ARRAY", "items": {"type": "STRING"}},
            "raw_transcript": {"type": "STRING"}
        },
        "required": ["type", "amount", "concept"]
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"Estructura este texto transcrito: '{transcript}' para el portafolio '{portfolio_name}'."}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
            "temperature": 0.1
        }
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    response = _http_client.post(GEMINI_API_URL, headers=headers, params=params, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Error en Gemini Text JSON: {response.text}")
    try:
        text_response = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed_transaction = json.loads(text_response)
        parsed_transaction["raw_transcript"] = transcript
        return parsed_transaction
    except Exception as e:
        raise RuntimeError(f"Fallo al parsear respuesta JSON de Gemini: {e}")


def parse_audio_to_transaction(
    audio_file_path: str,
    portfolio_name: str = "Negocio A"
) -> Dict[str, Any]:
    """
    Toma una grabación de micrófono, realiza la transcripción y el estructurado
    en un solo paso llamando a las subfunciones correspondientes.
    """
    transcript = transcribe_audio_only(audio_file_path)
    return structure_text_only(transcript, portfolio_name)
