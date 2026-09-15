/* ============================================================
   perspectiveBoot.js — Inicialización única de @finos/perspective.

   Los WASM viajan como ASSETS (?url → dist/assets/*.wasm) y se
   inicializan una sola vez, igual que hacen los builds "inline"
   oficiales pero sin inflar el chunk JS con base64 (~7MB menos).
   OJO lección RRHH: nada de grupos de chunk en vite.config para
   estas dependencias — el import perezoso del módulo basta.
   ============================================================ */
import perspective from '@finos/perspective';
import perspective_viewer from '@finos/perspective-viewer';
import '@finos/perspective-viewer-datagrid';
import '@finos/perspective-viewer-d3fc';
import '@finos/perspective-viewer/dist/css/pro.css';

import SERVER_WASM from '@finos/perspective/dist/wasm/perspective-server.wasm?url';
import CLIENT_WASM from '@finos/perspective/dist/wasm/perspective-js.wasm?url';
import VIEWER_WASM from '@finos/perspective-viewer/dist/wasm/perspective-viewer.wasm?url';

let _listo = null;
let _worker = null;

/** Inicializa los tres WASM (una vez) y devuelve el worker compartido. */
export async function obtenerWorker() {
  if (!_listo) {
    _listo = Promise.all([
      perspective.init_server(fetch(SERVER_WASM)),
      perspective.init_client(fetch(CLIENT_WASM)),
      perspective_viewer.init_client(fetch(VIEWER_WASM)),
    ]);
  }
  await _listo;
  if (!_worker) {
    _worker = await perspective.worker();
  }
  return _worker;
}
