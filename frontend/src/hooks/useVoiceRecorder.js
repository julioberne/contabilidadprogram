/* ============================================================
   useVoiceRecorder.js — Hook de grabación, transcripción y
   estructuración de audio para transacciones por voz.
   Extraído de App.jsx (estados L146-156, funciones L742-861)
   ============================================================ */
import { useState, useRef } from 'react';
import { API } from '../config';

const API_BASE_URL = API;

export default function useVoiceRecorder({ activePortfolio, setDrafts }) {
  // --- Estados del Grabador ---
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isStructuring, setIsStructuring] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");

  // --- Refs ---
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  // --- Transcribir audio ---
  const handleTranscribeAudio = async (audioBlob) => {
    setIsTranscribing(true);
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "grabacion.webm");

    try {
      const res = await fetch(`${API_BASE_URL}/transactions/transcribe`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      
      if (res.ok && data.transcript) {
        setLiveTranscript(prev => {
          const newText = data.transcript.trim();
          if (!prev) return newText;
          const separator = prev.endsWith(" ") ? "" : " ";
          return prev + separator + newText;
        });
      } else {
        const errorMsg = data?.detail || "Error al transcribir.";
        alert(`⚠️ No se pudo transcribir el audio. Detalle: ${errorMsg}`);
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor para transcribir.");
    } finally {
      setIsTranscribing(false);
    }
  };

  // --- Iniciar grabación ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      
      let options = { mimeType: 'audio/webm;codecs=opus' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = { mimeType: 'audio/webm' };
      }
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = { mimeType: 'audio/ogg;codecs=opus' };
      }
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = {};
      }
      
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const mimeTypeUsed = mediaRecorderRef.current.mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeTypeUsed });
        
        if (audioBlob.size < 1000) {
          alert("⚠️ Grabación demasiado corta o vacía. Asegúrate de hablar claramente frente al micrófono.");
        } else {
          await handleTranscribeAudio(audioBlob);
        }
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start(250);
      setIsRecording(true);
      setRecordingDuration(0);
      timerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
    } catch (err) {
      alert("❌ Error al acceder al micrófono. Asegúrate de otorgar los permisos necesarios.");
    }
  };

  // --- Detener grabación ---
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  // --- Estructurar transcripción con IA ---
  const handleStructureTranscript = async () => {
    if (!liveTranscript.trim()) {
      alert("⚠️ Escribe o graba algo de texto antes de procesar.");
      return;
    }
    
    setIsStructuring(true);
    try {
      const res = await fetch(`${API_BASE_URL}/transactions/structure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: liveTranscript,
          portfolio_name: activePortfolio
        })
      });
      const data = await res.json();
      
      if (res.ok && data.status === "BORRADOR") {
        setDrafts(prev => [data, ...prev]);
        setLiveTranscript("");
      } else {
        const errorDetail = typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail;
        alert(`⚠️ No se pudo estructurar el texto. Detalle: ${errorDetail || "Verifica tu API Key."}`);
      }
    } catch (error) {
      alert("❌ Error al estructurar el texto en el servidor.");
    } finally {
      setIsStructuring(false);
    }
  };

  return {
    // Estados
    isRecording,
    recordingDuration,
    isTranscribing,
    isStructuring,
    liveTranscript,
    setLiveTranscript,
    // Handlers
    startRecording,
    stopRecording,
    handleStructureTranscript,
  };
}
