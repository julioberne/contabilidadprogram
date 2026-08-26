# 🎙️ Guía de Motor de Voz — FIN-SYS OS v2.0

> **Estado**: ✅ Implementado con Groq Cloud (Whisper + Llama 3.3)
> **Actualización**: 09 Junio 2026

---

## Arquitectura Actual (Decisión Final)

El motor de voz usa un flujo de **dos etapas desacopladas** vía Groq Cloud:

```
[Audio WebM/Opus del Navegador]
         │
         ▼ ← Groq Whisper-large-v3 (latencia: ~0.2s)
[Texto transcrito en español]
         │
         ▼ ← RAG pgvector (búsqueda semántica de terceros recurrentes)
         │
         ▼ ← Llama 3.3-70b-versatile (estructuración JSON estricta)
[JSON BORRADOR → guardado en Supabase]
```

**Latencia total**: ~0.6s – 0.8s (vs ~3.5s con Gemini Multimodal todo-en-uno)

---

## Variables de Entorno Requeridas

```env
GROQ_API_KEY=gsk_...            # Requerida (gratis en console.groq.com)
GEMINI_API_KEY=...              # Fallback opcional
```

---

## Comparativa de Alternativas Evaluadas

| Criterio | Gemini Multimodal (descartado) | OpenAI Whisper | **Groq Whisper ✅ (actual)** | Web Speech API |
|---|---|---|---|---|
| Latencia | 2.5–4.5s | 0.9–1.5s | **0.15–0.3s** 🚀 | 0s (local) |
| Precisión ES | Alta | Muy Alta | Muy Alta | Regular |
| Costo | Free tier | $0.006/min | **Gratis** | 100% Gratis |
| Complejidad | Alta | Baja | **Baja** | Alta |

### ¿Por qué NO Gemini Multimodal para voz?
Pedirle a un modelo multimodal que haga todo al mismo tiempo (escuchar audio → transcribir → buscar RAG → formatear JSON estricto) es muy costoso en cómputo. La latencia de 3–5s hace la UX inaceptable.

### ¿Por qué NO Web Speech API?
Aunque es instantánea, la calidad en español para términos contables (NITs, montos, nombres de empresas) es propensa a errores y no permite inyectar contexto RAG.

---

## Implementación en `ai_engine.py`

```python
# Paso 1: STT con Groq Whisper
groq_client = Groq(api_key=GROQ_API_KEY)
transcription = groq_client.audio.transcriptions.create(
    file=("audio.webm", audio_bytes),
    model="whisper-large-v3",
    language="es"
)
raw_text = transcription.text

# Paso 2: Búsqueda semántica RAG (pgvector)
# Genera embedding del texto → busca terceros históricos similares
context = buscar_tercero_rag(raw_text)

# Paso 3: Estructuración con Llama 3.3
response = groq_client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": f"Estructurar: {raw_text}\nContexto: {context}"}],
    response_format={"type": "json_object"}
)
structured = json.loads(response.choices[0].message.content)
```

---

## Troubleshooting de Voz

| Síntoma | Causa | Solución |
|---|---|---|
| Audio envía 44 bytes | MediaRecorder no captura con timeslice | Verificar `start(250)` en el recorder |
| Error 400 de Groq | Audio vacío o codec inválido | Validar blob > 1KB antes de enviar |
| Borrador con todos los campos null | Llama no estructura bien | Verificar prompt en `ai_engine.py` |
| `"null"` literal en formulario | IA retorna string "null" | Sanitización activa en App.jsx |
