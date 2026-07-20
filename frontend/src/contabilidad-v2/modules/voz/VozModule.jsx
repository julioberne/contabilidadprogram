/* ============================================================
   VozModule.jsx — Adapter del widget de Voz IA (Módulo 03)
   Monta VoiceIngestWidget de v1 VERBATIM con useVoiceRecorder
   (imports transitorios desde components/ y hooks/; se vuelven
   internos en la Fase 7). Los borradores viven en el
   TransactionDraftProvider (compartidos voz ↔ registro).
   ============================================================ */
import { useState } from 'react';
import VoiceIngestWidget from '../../../components/VoiceIngestWidget.jsx';
import useVoiceRecorder from '../../../hooks/useVoiceRecorder.js';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';
import { useTransactionDraft } from '../../engine/TransactionDraftProvider.jsx';

export default function VozModule() {
  const { activePortfolio } = useEmpresa();
  const { drafts, setDrafts, loadDraftIntoForm } = useTransactionDraft();

  // En v1 este estado vivía en App.jsx
  const [showVoiceWidget, setShowVoiceWidget] = useState(false);

  const {
    isRecording, recordingDuration, isTranscribing, isStructuring,
    liveTranscript, setLiveTranscript,
    startRecording, stopRecording, handleStructureTranscript,
  } = useVoiceRecorder({ activePortfolio, setDrafts });

  return (
    <VoiceIngestWidget
      showVoiceWidget={showVoiceWidget}
      setShowVoiceWidget={setShowVoiceWidget}
      isRecording={isRecording}
      recordingDuration={recordingDuration}
      isTranscribing={isTranscribing}
      isStructuring={isStructuring}
      liveTranscript={liveTranscript}
      setLiveTranscript={setLiveTranscript}
      startRecording={startRecording}
      stopRecording={stopRecording}
      handleStructureTranscript={handleStructureTranscript}
      drafts={drafts}
      loadDraftIntoForm={loadDraftIntoForm}
    />
  );
}
