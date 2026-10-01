/* ============================================================
   tg/main.jsx — Entrada de la Mini App de Telegram (etapa 09.I).
   Misma API, misma sesión (finsys_session) y mismos componentes
   que la web; sin shell ni sidebar: una sola pantalla.
   ============================================================ */
import '../shell/installAuthFetch.js'; // PRIMERO: todo fetch a la API lleva el token
import { createRoot } from 'react-dom/client';
import '../index.css';
import TelegramTerceroApp from './TelegramTerceroApp.jsx';
import { tgReady } from './telegram.js';

tgReady();
createRoot(document.getElementById('root')).render(<TelegramTerceroApp />);
