/* compendio_visor.js — Visor del Compendio para el cliente (spec 13.6).
   Se incrusta en compendio_visor.html: lo sirve el backend en /c/<código> y,
   más adelante, el HTML offline (mismos datos, comprobantes en data:).
   Todo se arma con textContent/createElement: ningún dato entra como HTML. */
(function () {
  'use strict';
  var D = JSON.parse(document.getElementById('datos').textContent);
  var app = document.getElementById('app');

  function el(tag, props, hijos) {
    var n = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      var v = props[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'text') n.textContent = v;
      else if (k === 'class') n.className = v;
      else if (k.slice(0, 2) === 'on') n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? '' : v);
    });
    (hijos || []).forEach(function (h) { if (h) n.appendChild(typeof h === 'string' ? document.createTextNode(h) : h); });
    return n;
  }
  function plata(v, moneda) {
    var s = Number(v || 0).toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    return (moneda === 'COP' ? '$' : moneda + ' ') + s;
  }
  function dia(iso) {
    if (!iso) return '—';
    var p = String(iso).slice(0, 10).split('-');
    return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : iso;
  }
  function sinTildes(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  function abrirData(uri) {
    var partes = String(uri).split(',');
    var bin = atob(partes[1] || '');
    var bytes = new Uint8Array(bin.length);
    for (var k = 0; k < bin.length; k++) bytes[k] = bin.charCodeAt(k);
    var mime = (partes[0] || '').slice(5).split(';')[0] || 'application/octet-stream';
    window.open(URL.createObjectURL(new Blob([bytes], { type: mime })), '_blank');
  }
  function urlSoporte(t, s) { return s.data || (D.base + '/soporte/' + t.i + '/' + s.j + (D.previa ? '?previa=1' : '')); }

  // ── Cabecera y totales ─────────────────────────────────────────────
  var empresas = (D.empresas || []).map(function (e) { return e.nombre + (e.nit ? ' · NIT ' + e.nit : ''); }).join(' — ');
  var cabecera = el('section', { class: 'caja' }, [
    el('h1', { text: D.nombre || 'Compendio' }),
    el('div', { class: 'meta' }, [
      empresas ? el('span', { text: empresas }) : null,
      el('span', { text: 'Folio ' + (D.folio || '—') }),
      D.rango && D.rango.desde ? el('span', { text: dia(D.rango.desde) + ' a ' + dia(D.rango.hasta) }) : null,
      el('span', { text: D.n + ' transacción' + (D.n === 1 ? '' : 'es') }),
      D.expira_en && !D.offline ? el('span', { text: 'Válido hasta el ' + dia(D.expira_en) }) : null,
      D.offline ? el('span', { class: 'chip', text: '💾 Copia offline generada el ' + dia(D.generado) + ' (no necesita internet)' }) : null,
      D.previa ? el('span', { class: 'chip', text: '👁 Vista previa interna: no cuenta como visita del cliente' }) : null,
    ]),
    D.nota ? el('div', { class: 'nota', text: D.nota }) : null,
  ]);
  var chips = el('div', { class: 'chips' });
  Object.keys(D.totales || {}).forEach(function (m) {
    var t = D.totales[m];
    chips.appendChild(el('span', { class: 'chip ing', text: '▲ Ingresos ' + plata(t.ingresos, m) }));
    chips.appendChild(el('span', { class: 'chip gas', text: '▼ Gastos ' + plata(t.gastos, m) }));
    chips.appendChild(el('span', { class: 'chip net', text: '∑ Neto ' + plata(t.neto, m) }));
  });
  var totales = el('section', { class: 'caja', 'aria-label': 'Totales' }, [chips]);

  // ── Filtros ────────────────────────────────────────────────────────
  var txs = D.txs || [];
  var tipos = []; var categorias = [];
  txs.forEach(function (t) {
    if (t.tipo && tipos.indexOf(t.tipo) < 0) tipos.push(t.tipo);
    if (t.categoria && categorias.indexOf(t.categoria) < 0) categorias.push(t.categoria);
  });
  categorias.sort(function (a, b) { return a.localeCompare(b, 'es'); });
  function opciones(sel, todos, lista) {
    sel.appendChild(el('option', { value: '', text: todos }));
    lista.forEach(function (v) { sel.appendChild(el('option', { value: v, text: v })); });
    return sel;
  }
  var q = el('input', { type: 'search', placeholder: '🔍 Buscar concepto, tercero, categoría…', 'aria-label': 'Buscar' });
  var fTipo = opciones(el('select', { 'aria-label': 'Tipo' }), 'Todo tipo', tipos);
  var fCat = opciones(el('select', { 'aria-label': 'Categoría' }), 'Toda categoría', categorias);
  var fOrden = el('select', { 'aria-label': 'Orden' }, [
    el('option', { value: 'fecha', text: 'Fecha ↑' }), el('option', { value: '-fecha', text: 'Fecha ↓' }),
    el('option', { value: '-valor', text: 'Valor ↓' }),
  ]);
  var cuenta = el('p', { class: 'cuenta' });
  var lista = el('ol', { class: 'lista' });
  var seccionLista = el('section', { class: 'caja' }, [el('div', { class: 'controles' }, [q, fTipo, fCat, fOrden]), cuenta, lista]);
  [q, fTipo, fCat, fOrden].forEach(function (c) { c.addEventListener('input', pintar); });

  // ── Lupa para las fotos ────────────────────────────────────────────
  function lupa(src, alt) {
    var capa = el('div', { class: 'lupa', role: 'dialog', 'aria-label': alt }, [el('img', { src: src, alt: alt })]);
    function cerrar() { capa.remove(); document.removeEventListener('keydown', tecla); }
    function tecla(e) { if (e.key === 'Escape') cerrar(); }
    capa.addEventListener('click', cerrar);
    document.addEventListener('keydown', tecla);
    document.body.appendChild(capa);
  }

  // ── Detalle de una transacción ─────────────────────────────────────
  var ancho = window.matchMedia ? window.matchMedia('(min-width: 700px)').matches : true;
  function dato(etiqueta, valor) { return valor ? el('div', null, [el('b', { text: etiqueta }), valor]) : null; }
  function detalle(t) {
    var datos = el('div', { class: 'datos' }, [
      dato('Empresa', t.empresa), dato('Tercero', t.tercero), dato('Identificación', t.identificacion),
      dato('Categoría', t.categoria), dato('Cuenta', t.cuenta),
      dato('Valor bruto', t.bruto ? plata(t.bruto, t.moneda) : ''), dato('IVA', t.iva ? plata(t.iva, t.moneda) : ''),
      dato('GMF', t.gmf ? plata(t.gmf, t.moneda) : ''), dato('Valor neto', plata(t.neto, t.moneda)),
      dato('Referencia', '#' + t.id),
    ]);
    var acciones = el('div', null, [t.maps ? el('a', { class: 'boton', href: t.maps, target: '_blank', rel: 'noopener noreferrer',
      text: '📍 Ver en Google Maps' }) : null]);
    var galeria = el('div', { class: 'galeria' });
    var sops = t.soportes || [];
    if (!sops.length) galeria.appendChild(el('p', { class: 'no-disp', text: 'Esta transacción no tiene comprobantes.' }));
    sops.forEach(function (s, k) {
      var titulo = 'Comprobante ' + (k + 1);
      var caja = el('figure', { class: 'soporte' });
      if (!s.servible) {
        caja.appendChild(el('p', { class: 'no-disp', text: titulo + ': ' + (s.nota || 'no disponible') }));
      } else if (s.tipo === 'pdf' && s.data) {
        // Offline: Chrome no deja abrir un data: como página; se abre como blob en otra pestaña.
        caja.appendChild(el('button', { class: 'boton', type: 'button', text: '📄 Abrir PDF',
          onclick: function () { abrirData(s.data); } }));
      } else if (s.tipo === 'imagen') {
        var src = urlSoporte(t, s);
        caja.appendChild(el('img', { src: src, alt: titulo, loading: 'lazy', onclick: function () { lupa(src, titulo); } }));
      } else if (s.tipo === 'pdf') {
        if (ancho && !s.data) caja.appendChild(el('iframe', { src: urlSoporte(t, s), title: titulo, loading: 'lazy' }));
        caja.appendChild(el('a', { class: 'boton', href: urlSoporte(t, s), target: '_blank', rel: 'noopener', text: '📄 Abrir PDF' }));
      } else if (s.tipo === 'audio') {
        caja.appendChild(el('audio', { src: urlSoporte(t, s), controls: true, preload: 'none' }));
      } else {
        caja.appendChild(el('a', { class: 'boton', href: urlSoporte(t, s), download: s.nombre, text: '⬇ Descargar' }));
      }
      caja.appendChild(el('figcaption', { class: 'pie', text: titulo + (s.nombre ? ' · ' + s.nombre : '') }));
      galeria.appendChild(caja);
    });
    return el('div', { class: 'detalle' }, [datos, acciones, galeria]);
  }

  // ── 13.6-c: avisar al servidor qué transacción se abrió (una vez por página) ──
  var avisadas = {};
  function avisar(t) {
    if (D.offline || D.previa || avisadas[t.i] || !window.fetch) return;
    avisadas[t.i] = true;
    try {
      fetch(D.base + '/evento', { method: 'POST', keepalive: true, credentials: 'omit',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tipo: 'tx', i: t.i }) })
        .catch(function () {});
    } catch (e) { /* el seguimiento jamás estorba al cliente */ }
  }

  // ── Lista ──────────────────────────────────────────────────────────
  var abierta = null;
  function fila(t) {
    var li = el('li');
    var n = (t.soportes || []).length;
    var boton = el('button', { class: 'fila', type: 'button', 'aria-expanded': 'false' }, [
      el('span', { class: 'fecha', text: dia(t.fecha) }),
      el('span', null, [
        el('span', { class: 'tipo t-' + t.tipo, text: (t.tipo || '').slice(0, 3) }),
        el('span', { class: 'concepto', text: t.concepto || '(sin concepto)' }),
        el('div', { class: 'sub', text: [t.tercero, t.categoria].filter(Boolean).join(' · ') }),
      ]),
      el('span', null, [
        el('div', { class: 'valor', text: plata(t.neto, t.moneda) }),
        el('div', { class: 'marcas', text: (n ? '📎' + n : '') + (t.maps ? ' 📍' : '') }),
      ]),
    ]);
    boton.addEventListener('click', function () {
      var ya = li.querySelector('.detalle');
      if (ya) { ya.remove(); boton.setAttribute('aria-expanded', 'false'); abierta = null; return; }
      if (abierta) abierta();
      li.appendChild(detalle(t));
      avisar(t);
      boton.setAttribute('aria-expanded', 'true');
      abierta = function () { var d = li.querySelector('.detalle'); if (d) d.remove(); boton.setAttribute('aria-expanded', 'false'); };
    });
    li.appendChild(boton);
    return li;
  }
  function pintar() {
    var texto = sinTildes(q.value).trim().split(/\s+/).filter(Boolean);
    var vis = txs.filter(function (t) {
      if (fTipo.value && t.tipo !== fTipo.value) return false;
      if (fCat.value && t.categoria !== fCat.value) return false;
      var hay = sinTildes([t.concepto, t.tercero, t.categoria, t.empresa, t.cuenta, t.id].join(' '));
      return texto.every(function (p) { return hay.indexOf(p) >= 0; });
    });
    var o = fOrden.value;
    vis.sort(function (a, b) {
      if (o === '-valor') return Math.abs(b.neto) - Math.abs(a.neto);
      var c = String(a.fecha || '').localeCompare(String(b.fecha || '')) || a.i - b.i;
      return o === '-fecha' ? -c : c;
    });
    abierta = null;
    lista.textContent = '';
    vis.forEach(function (t) { lista.appendChild(fila(t)); });
    if (!vis.length) lista.appendChild(el('li', { class: 'vacio', text: 'Nada coincide con la búsqueda.' }));
    cuenta.textContent = 'Mostrando ' + vis.length + ' de ' + txs.length;
  }

  var descargas = D.offline ? null : el('section', { class: 'caja', 'aria-label': 'Descargas' }, [
    el('a', { class: 'boton', href: D.base + '/pdf' + (D.previa ? '?previa=1' : ''), download: '',
      text: '⬇ Descargar PDF' }), ' ',
    el('a', { class: 'boton', href: D.base + '/html' + (D.previa ? '?previa=1' : ''), download: '',
      text: '💾 Descargar HTML offline' }),
    el('div', { class: 'sub', text: 'PDF: portada, índice y una página por transacción con sus comprobantes (para imprimir o archivar). ' +
      'HTML offline: este mismo compendio en un solo archivo que abre sin internet.' }),
  ]);
  var pie = el('footer', { text: 'Folio ' + (D.folio || '—') + ' · Generado con FIN-SYS' +
    (D.creado_en ? ' el ' + dia(D.creado_en) : '') + (D.expira_en ? ' · Este enlace vence el ' + dia(D.expira_en) : '') });
  app.textContent = '';
  [cabecera, totales, seccionLista, descargas, pie].forEach(function (s) { if (s) app.appendChild(s); });
  pintar();
})();
