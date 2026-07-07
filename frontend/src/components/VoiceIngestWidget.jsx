// VoiceIngestWidget.jsx — Extracted from App.jsx (Lines 631-742)
import React from 'react';

export default function VoiceIngestWidget({
  showVoiceWidget,
  setShowVoiceWidget,
  isRecording,
  recordingDuration,
  isTranscribing,
  isStructuring,
  liveTranscript,
  setLiveTranscript,
  startRecording,
  stopRecording,
  handleStructureTranscript,
  drafts,
  loadDraftIntoForm,
}) {
  return (
    <div className="border-2 border-black bg-white shadow-brutal">
      <div
        onClick={() => setShowVoiceWidget(prev => !prev)}
        className="p-2 cursor-pointer flex justify-between items-center hover:bg-brutalBg transition-all"
      >
        <span className="text-[10px] font-bold uppercase font-mono">
          {showVoiceWidget ? '[x] 🎤 VOZ IA — INGESTIÓN INTELIGENTE' : '[+] 🎤 VOZ IA — INGESTIÓN INTELIGENTE'}
        </span>
        <span className="text-[9px] font-mono text-gray-400">
          {isRecording ? '🔴 Grabando...' : drafts.length > 0 ? `${drafts.length} borradores` : 'Click para grabar'}
        </span>
      </div>
      {showVoiceWidget && (
    <div className="bg-white border-2 border-black p-2 shadow-brutal">
      <h2 className="text-sm font-bold uppercase border-b-2 border-black pb-1 mb-2">🎤 Ingestión por Voz Inteligente</h2>
      <p className="text-xs text-gray-500 uppercase leading-relaxed mb-2">
        Presiona el micrófono y registra libremente. Llama 3.3 y RAG autocompletarán los datos recurrentes como borradores.
      </p>

      <div className="flex flex-col items-center justify-center p-2 border-2 border-dashed border-black bg-brutalBg">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={isTranscribing || isStructuring}
            className="w-16 h-16 rounded-full bg-brutalGreen border-3 border-black flex items-center justify-center shadow-brutal hover:translate-y-0.5 active:translate-y-1 transition-all disabled:opacity-50"
            type="button"
          >
            <span className="text-2xl">🎙️</span>
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="w-16 h-16 rounded-full bg-brutalCrimson border-3 border-black flex items-center justify-center animate-pulse shadow-brutal"
            type="button"
          >
            <span className="text-white text-2xl">⏹️</span>
          </button>
        )}

        <span className="text-sm font-bold uppercase mt-3 tracking-wider">
          {isRecording ? `Grabando: ${recordingDuration}s` : isTranscribing ? "Transcribiendo audio..." : isStructuring ? "IA Estructurando..." : "Listo para grabar"}
        </span>

        {(isTranscribing || isStructuring) && (
          <div className="w-full bg-gray-200 border-2 border-black h-4 mt-4 overflow-hidden relative">
            <div className="bg-brutalGreen border-r-2 border-black h-full w-1/2 animate-ping"></div>
          </div>
        )}
      </div>

      {/* Consola de Transcripción Editable */}
      <div className="mt-2 border-2 border-black bg-brutalBg p-2 space-y-1">
        <span className="text-xs font-bold uppercase text-gray-500 block">📝 Consola de Transcripción (Editable)</span>
        <textarea
          value={liveTranscript}
          onChange={(e) => setLiveTranscript(e.target.value)}
          placeholder="Presiona el micrófono y habla, o escribe directamente aquí para estructurar..."
          className="w-full h-24 bg-white border-2 border-black p-2 text-xs font-mono outline-none resize-none focus:border-brutalGreen"
          disabled={isTranscribing || isStructuring}
        />
        <button
          type="button"
          onClick={handleStructureTranscript}
          disabled={isTranscribing || isStructuring || !liveTranscript.trim()}
          className="w-full bg-brutalGreen text-black hover:bg-black hover:text-white border-2 border-black py-2 text-xs font-bold uppercase transition-all disabled:opacity-50"
        >
          {isStructuring ? "PROCESANDO CON IA..." : "⚡ PROCESAR CON IA"}
        </button>
      </div>

      {/* Bandeja de Borradores de Voz (Draft Inbox) */}
      {drafts.length > 0 && (
        <div className="mt-6 border-t-2 border-black pt-4">
          <span className="text-xs font-bold uppercase text-gray-400 block mb-2">📥 Borradores de Voz Pendientes</span>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {drafts.map((d, index) => (
              <div 
                key={index}
                onClick={() => loadDraftIntoForm(d)}
                className="border-2 border-black bg-white p-2 hover:bg-brutalNeutral cursor-pointer flex flex-col justify-between transition-all"
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs bg-brutalAmber border border-black px-1 py-0.5 font-bold uppercase text-black">
                    {d.inferred_fields?.length > 0 ? "Borrador Incompleto" : "Completo"}
                  </span>
                  <span className="text-xs font-bold">${d.parsed_data?.amount}</span>
                </div>
                <p className="text-xs font-bold uppercase mt-2 line-clamp-1">"{d.parsed_data?.concept}"</p>
                
                {/* Mostrar transcripción raw completa en la tarjeta */}
                {d.raw_transcript && (
                  <p className="text-[10px] text-gray-500 mt-1 italic border-l-2 border-black pl-1.5 line-clamp-2">
                    "{d.raw_transcript}"
                  </p>
                )}

                {d.inferred_fields?.length > 0 && (
                  <span className="text-[10px] text-brutalCrimson font-bold uppercase mt-1">
                    ⚠️ Falta: {d.inferred_fields.join(", ")}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
      )}
    </div>
  );
}
