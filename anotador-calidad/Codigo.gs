/**
 * ANOTADOR DEL EQUIPO DE GESTIÓN DE CALIDAD
 * -----------------------------------------
 * Planilla de Google + recordatorios automáticos por mail (y opcional WhatsApp).
 *
 * - La hoja "Tareas" es el anotador: una fila por tema/tarea, con fecha de vencimiento opcional.
 * - La hoja "Equipo" tiene a quién avisar.
 * - Todos los días a las CONFIG.HORA_AVISO se revisa el anotador y, si hay algo vencido,
 *   que vence hoy o que está por vencer, se manda un mail al equipo. Los lunes se manda
 *   siempre el resumen completo de la semana.
 * - El mail trae un botón "Reenviar al grupo de WhatsApp" con el mensaje ya armado.
 * - Opcional: página web (celular) para ver la lista y cargar tareas con una clave.
 *
 * Instalación: ver README.md (menú 📋 Anotador → "Configurar anotador").
 */

const CONFIG = {
  NOMBRE_EQUIPO: 'Gestión de Calidad',
  HOJA_TAREAS: 'Tareas',
  HOJA_EQUIPO: 'Equipo',
  HORA_AVISO: 8,              // hora del aviso diario (0-23)
  DIAS_AVISO_DEFECTO: 3,      // si no se completa "Avisar (días antes)"
  RESUMEN_SEMANAL_DIA: 1,     // 0=domingo, 1=lunes ... resumen completo aunque no haya urgencias
  CLAVE_CARGA: 'calidad2026', // clave para cargar / cerrar tareas desde la página web. ¡CAMBIARLA!
};

const TIPOS = ['Relevamiento', 'Auditoría', 'Capacitación', 'Reunión', 'Documento', 'Indicador', 'Recordatorio', 'Otro'];
const ESTADOS = ['Pendiente', 'En curso', 'Hecho'];
const COLS = ['N°', 'Cargado', 'Tema / Tarea', 'Tipo', 'Responsable', 'Vence', 'Avisar (días antes)', 'Estado', 'Notas'];
const COL = { ID: 1, CARGADO: 2, TAREA: 3, TIPO: 4, RESPONSABLE: 5, VENCE: 6, AVISO: 7, ESTADO: 8, NOTAS: 9 };
const COLS_EQUIPO = ['Nombre', 'Email', 'Recibe mail (Sí/No)', 'WhatsApp (opcional, ej. 5493415551234)', 'Clave CallMeBot (opcional)'];

// ---------------------------------------------------------------- menú y configuración

function onOpen() {
  SpreadsheetApp.getUi().createMenu('📋 Anotador')
    .addItem('Configurar anotador (una sola vez)', 'configurar')
    .addSeparator()
    .addItem('Ver mensaje para WhatsApp', 'mostrarMensajeWhatsApp')
    .addItem('Enviar resumen por mail ahora', 'enviarResumenAhora')
    .addToUi();
}

function configurar() {
  const ss = SpreadsheetApp.getActive();

  const tareas = ss.getSheetByName(CONFIG.HOJA_TAREAS) || ss.insertSheet(CONFIG.HOJA_TAREAS, 0);
  tareas.getRange(1, 1, 1, COLS.length).setValues([COLS])
    .setFontWeight('bold').setBackground('#1f4e79').setFontColor('#ffffff').setWrap(true);
  tareas.setFrozenRows(1);
  const n = tareas.getMaxRows() - 1;
  const regla = SpreadsheetApp.newDataValidation;
  tareas.getRange(2, COL.TIPO, n).setDataValidation(regla().requireValueInList(TIPOS, true).build());
  tareas.getRange(2, COL.ESTADO, n).setDataValidation(regla().requireValueInList(ESTADOS, true).build());
  tareas.getRange(2, COL.VENCE, n).setDataValidation(regla().requireDate().setAllowInvalid(false).build());
  tareas.getRange(2, COL.AVISO, n).setDataValidation(regla().requireNumberBetween(0, 90).build());
  tareas.getRange(2, COL.CARGADO, n).setNumberFormat('dd/mm/yyyy');
  tareas.getRange(2, COL.VENCE, n).setNumberFormat('dd/mm/yyyy');
  [50, 85, 320, 110, 130, 90, 90, 90, 260].forEach((w, i) => tareas.setColumnWidth(i + 1, w));

  // Colores: gris = hecho, rojo = vencida, amarillo = por vencer.
  const rango = tareas.getRange(2, 1, n, COLS.length);
  const formato = f => SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied(f).setRanges([rango]);
  tareas.setConditionalFormatRules([
    formato('=$H2="Hecho"').setFontColor('#999999').setStrikethrough(true).build(),
    formato('=AND($F2<>"",$F2<TODAY())').setBackground('#f8d7da').build(),
    formato(`=AND($F2<>"",$F2-TODAY()<=IF($G2="",${CONFIG.DIAS_AVISO_DEFECTO},$G2))`).setBackground('#fff3cd').build(),
  ]);

  const equipo = ss.getSheetByName(CONFIG.HOJA_EQUIPO) || ss.insertSheet(CONFIG.HOJA_EQUIPO);
  equipo.getRange(1, 1, 1, COLS_EQUIPO.length).setValues([COLS_EQUIPO])
    .setFontWeight('bold').setBackground('#1f4e79').setFontColor('#ffffff').setWrap(true);
  equipo.setFrozenRows(1);
  equipo.getRange(2, 3, equipo.getMaxRows() - 1)
    .setDataValidation(regla().requireValueInList(['Sí', 'No'], true).build());
  equipo.getRange(2, 4, equipo.getMaxRows() - 1).setNumberFormat('@');
  [160, 240, 110, 230, 160].forEach((w, i) => equipo.setColumnWidth(i + 1, w));

  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'avisoDiario')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('avisoDiario').timeBased().everyDays(1).atHour(CONFIG.HORA_AVISO).create();

  SpreadsheetApp.getUi().alert(
    '✅ Anotador listo.\n\n' +
    '1) Cargá al equipo en la hoja "' + CONFIG.HOJA_EQUIPO + '" (nombre y mail).\n' +
    '2) Cargá los temas en la hoja "' + CONFIG.HOJA_TAREAS + '".\n\n' +
    'Todos los días a las ' + CONFIG.HORA_AVISO + ' hs se avisará lo que esté vencido o por vencer.');
}

// Al escribir una tarea nueva directo en la planilla, completa N°, fecha de carga y estado.
function onEdit(e) {
  const hoja = e.range.getSheet();
  if (hoja.getName() !== CONFIG.HOJA_TAREAS || e.range.getRow() < 2) return;
  if (e.range.getColumn() > COL.TAREA || e.range.getLastColumn() < COL.TAREA) return;
  for (let fila = e.range.getRow(); fila <= e.range.getLastRow(); fila++) {
    const valores = hoja.getRange(fila, 1, 1, COL.ESTADO).getValues()[0];
    if (!String(valores[COL.TAREA - 1]).trim() || valores[COL.ID - 1] !== '') continue;
    hoja.getRange(fila, COL.ID).setValue(siguienteId_(hoja));
    if (!valores[COL.CARGADO - 1]) hoja.getRange(fila, COL.CARGADO).setValue(hoyCero_());
    if (!valores[COL.ESTADO - 1]) hoja.getRange(fila, COL.ESTADO).setValue('Pendiente');
  }
}

// ---------------------------------------------------------------- lectura y clasificación

function hojaTareas_() {
  return SpreadsheetApp.getActive().getSheetByName(CONFIG.HOJA_TAREAS);
}

function siguienteId_(hoja) {
  const ult = hoja.getLastRow();
  if (ult < 2) return 1;
  const ids = hoja.getRange(2, COL.ID, ult - 1).getValues().map(f => Number(f[0]) || 0);
  return Math.max(0, ...ids) + 1;
}

function leerTareas_() {
  const hoja = hojaTareas_();
  const ult = hoja.getLastRow();
  if (ult < 2) return [];
  return hoja.getRange(2, 1, ult - 1, COLS.length).getValues()
    .map((f, i) => ({
      fila: i + 2,
      id: f[COL.ID - 1],
      tarea: String(f[COL.TAREA - 1]).trim(),
      tipo: f[COL.TIPO - 1],
      responsable: f[COL.RESPONSABLE - 1],
      vence: f[COL.VENCE - 1] instanceof Date ? f[COL.VENCE - 1] : null,
      aviso: f[COL.AVISO - 1] === '' ? CONFIG.DIAS_AVISO_DEFECTO : Number(f[COL.AVISO - 1]),
      estado: f[COL.ESTADO - 1] || 'Pendiente',
      notas: f[COL.NOTAS - 1],
    }))
    .filter(t => t.tarea);
}

function leerEquipo_() {
  const hoja = SpreadsheetApp.getActive().getSheetByName(CONFIG.HOJA_EQUIPO);
  if (!hoja || hoja.getLastRow() < 2) return [];
  return hoja.getRange(2, 1, hoja.getLastRow() - 1, COLS_EQUIPO.length).getValues()
    .map(f => ({
      nombre: f[0],
      email: String(f[1]).trim(),
      recibeMail: String(f[2]).trim().toLowerCase() !== 'no',
      whatsapp: String(f[3]).replace(/\D/g, ''),
      claveCallMeBot: String(f[4]).trim(),
    }));
}

function hoyCero_() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function diasHasta_(fecha) {
  const f = new Date(fecha);
  f.setHours(0, 0, 0, 0);
  return Math.round((f - hoyCero_()) / 86400000);
}

function clasificar_(tareas) {
  const g = { vencidas: [], hoy: [], proximas: [], adelante: [], sinFecha: [] };
  tareas.filter(t => t.estado !== 'Hecho').forEach(t => {
    if (!t.vence) return g.sinFecha.push(t);
    t.dias = diasHasta_(t.vence);
    if (t.dias < 0) g.vencidas.push(t);
    else if (t.dias === 0) g.hoy.push(t);
    else if (t.dias <= t.aviso) g.proximas.push(t);
    else g.adelante.push(t);
  });
  ['vencidas', 'hoy', 'proximas', 'adelante'].forEach(k => g[k].sort((a, b) => a.vence - b.vence));
  return g;
}

const GRUPOS = [
  { clave: 'vencidas', titulo: '🔴 Vencidas', color: '#f8d7da', siempre: true },
  { clave: 'hoy', titulo: '🟠 Vencen hoy', color: '#ffe5cc', siempre: true },
  { clave: 'proximas', titulo: '🟡 Por vencer', color: '#fff3cd', siempre: true },
  { clave: 'adelante', titulo: '🗓️ Más adelante', color: '#e8f0fe', siempre: false },
  { clave: 'sinFecha', titulo: '📌 Sin fecha', color: '#f1f3f4', siempre: false },
];

function fecha_(d) {
  return Utilities.formatDate(d, Session.getScriptTimeZone(), 'dd/MM/yyyy');
}

function cuando_(t) {
  if (!t.vence) return '';
  if (t.dias < 0) return -t.dias === 1 ? 'venció ayer' : `venció hace ${-t.dias} días`;
  if (t.dias === 0) return 'vence HOY';
  if (t.dias === 1) return 'vence mañana';
  return `vence en ${t.dias} días`;
}

function urlWeb_() {
  try { return ScriptApp.getService().getUrl() || ''; } catch (e) { return ''; }
}

// ---------------------------------------------------------------- mensajes

function textoWhatsApp_(g, completo) {
  const lineas = [`📋 *Anotador – ${CONFIG.NOMBRE_EQUIPO}*`, `_${fecha_(new Date())}_`];
  let hayAlgo = false;
  GRUPOS.filter(gr => gr.siempre || completo).forEach(gr => {
    if (!g[gr.clave].length) return;
    hayAlgo = true;
    lineas.push('', `*${gr.titulo}*`);
    g[gr.clave].forEach(t => {
      const extra = [t.tipo, t.responsable, t.vence && `${fecha_(t.vence)} (${cuando_(t)})`].filter(Boolean);
      lineas.push(`• ${t.tarea}${extra.length ? ' — ' + extra.join(' · ') : ''}`);
    });
  });
  if (!hayAlgo) lineas.push('', '✅ No hay nada pendiente con vencimiento cercano.');
  const url = urlWeb_();
  if (url) lineas.push('', `🔗 Ver anotador: ${url}`);
  return lineas.join('\n');
}

function htmlMail_(g, completo, textoWa) {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  let html = `<div style="font-family:Arial,sans-serif;max-width:640px">
    <h2 style="color:#1f4e79;margin-bottom:4px">📋 Anotador – ${esc(CONFIG.NOMBRE_EQUIPO)}</h2>
    <div style="color:#666;margin-bottom:16px">${fecha_(new Date())}</div>`;
  let hayAlgo = false;
  GRUPOS.filter(gr => gr.siempre || completo).forEach(gr => {
    if (!g[gr.clave].length) return;
    hayAlgo = true;
    html += `<h3 style="margin:18px 0 6px">${gr.titulo} (${g[gr.clave].length})</h3>
      <table style="border-collapse:collapse;width:100%;font-size:14px">`;
    g[gr.clave].forEach(t => {
      html += `<tr style="background:${gr.color}">
        <td style="padding:6px 8px;border-bottom:1px solid #fff"><b>${esc(t.tarea)}</b>
          ${t.notas ? `<br><span style="color:#555">${esc(t.notas)}</span>` : ''}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #fff">${esc(t.tipo)}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #fff">${esc(t.responsable)}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #fff;white-space:nowrap">
          ${t.vence ? fecha_(t.vence) + '<br><small>' + cuando_(t) + '</small>' : ''}</td></tr>`;
    });
    html += '</table>';
  });
  if (!hayAlgo) html += '<p>✅ No hay nada pendiente con vencimiento cercano.</p>';
  html += `<p style="margin-top:24px">
    <a href="https://wa.me/?text=${encodeURIComponent(textoWa)}"
       style="background:#25d366;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;font-weight:bold">
       📲 Reenviar al grupo de WhatsApp</a></p>
    <p style="font-size:13px"><a href="${SpreadsheetApp.getActive().getUrl()}">Abrir la planilla</a>
    ${urlWeb_() ? ` · <a href="${urlWeb_()}">Abrir el anotador en el celular</a>` : ''}</p></div>`;
  return html;
}

// ---------------------------------------------------------------- envíos

/** Lo ejecuta el disparador diario. */
function avisoDiario() {
  const g = clasificar_(leerTareas_());
  const urgentes = g.vencidas.length + g.hoy.length + g.proximas.length;
  const diaResumen = new Date().getDay() === CONFIG.RESUMEN_SEMANAL_DIA;
  if (!urgentes && !diaResumen) return;
  enviar_(g, diaResumen);
}

function enviarResumenAhora() {
  const enviados = enviar_(clasificar_(leerTareas_()), true);
  SpreadsheetApp.getUi().alert(enviados ? `✅ Resumen enviado a ${enviados} persona(s).`
    : '⚠️ No hay mails cargados en la hoja "' + CONFIG.HOJA_EQUIPO + '".');
}

function enviar_(g, completo) {
  const texto = textoWhatsApp_(g, completo);
  const equipo = leerEquipo_();

  const mails = equipo.filter(p => p.email && p.recibeMail).map(p => p.email);
  if (mails.length) {
    const partes = [
      g.vencidas.length && `${g.vencidas.length} vencida(s)`,
      g.hoy.length && `${g.hoy.length} vence(n) hoy`,
      g.proximas.length && `${g.proximas.length} por vencer`,
    ].filter(Boolean);
    MailApp.sendEmail({
      to: mails.join(','),
      subject: `📋 ${CONFIG.NOMBRE_EQUIPO}: ${partes.length ? partes.join(', ') : 'resumen semanal'}`,
      body: texto,
      htmlBody: htmlMail_(g, completo, texto),
    });
  }

  // WhatsApp automático individual vía CallMeBot (gratis, cada persona lo activa una vez).
  equipo.filter(p => p.whatsapp && p.claveCallMeBot).forEach(p => {
    try {
      UrlFetchApp.fetch('https://api.callmebot.com/whatsapp.php?phone=' + p.whatsapp +
        '&text=' + encodeURIComponent(texto) + '&apikey=' + encodeURIComponent(p.claveCallMeBot),
        { muteHttpExceptions: true });
    } catch (e) {
      console.warn('No se pudo enviar WhatsApp a ' + p.nombre + ': ' + e);
    }
  });

  return mails.length;
}

function mostrarMensajeWhatsApp() {
  const texto = textoWhatsApp_(clasificar_(leerTareas_()), true);
  const html = HtmlService.createHtmlOutput(
    `<div style="font-family:Arial,sans-serif">
      <p>Copiá este mensaje y pegalo en el grupo, o tocá el botón verde:</p>
      <textarea id="t" style="width:100%;height:300px">${texto.replace(/</g, '&lt;')}</textarea>
      <p><a target="_blank" href="https://wa.me/?text=${encodeURIComponent(texto)}"
        style="background:#25d366;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none">
        📲 Abrir en WhatsApp</a>
      <button onclick="document.getElementById('t').select();document.execCommand('copy')">Copiar</button></p>
    </div>`).setWidth(520).setHeight(440);
  SpreadsheetApp.getUi().showModalDialog(html, 'Mensaje para el grupo');
}

// ---------------------------------------------------------------- página web (celular)

function doGet() {
  return HtmlService.createTemplateFromFile('Web').evaluate()
    .setTitle('Anotador – ' + CONFIG.NOMBRE_EQUIPO)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function datosWeb() {
  const g = clasificar_(leerTareas_());
  const grupos = GRUPOS.map(gr => ({
    titulo: gr.titulo,
    color: gr.color,
    tareas: g[gr.clave].map(t => ({
      id: t.id, tarea: t.tarea, tipo: t.tipo, responsable: t.responsable, estado: t.estado,
      notas: t.notas, vence: t.vence ? fecha_(t.vence) : '', cuando: cuando_(t),
    })),
  })).filter(gr => gr.tareas.length);
  return { equipo: CONFIG.NOMBRE_EQUIPO, hoy: fecha_(new Date()), tipos: TIPOS, grupos };
}

function validarClave_(clave) {
  if (clave !== CONFIG.CLAVE_CARGA) throw new Error('Clave incorrecta');
}

function agregarTarea(d) {
  validarClave_(d.clave);
  if (!d.tarea || !String(d.tarea).trim()) throw new Error('Falta el tema / tarea');
  let vence = '';
  if (d.vence) {
    const [a, m, dia] = d.vence.split('-').map(Number);
    vence = new Date(a, m - 1, dia);
  }
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const hoja = hojaTareas_();
    hoja.appendRow([siguienteId_(hoja), hoyCero_(), String(d.tarea).trim(), d.tipo || '',
      d.responsable || '', vence, d.aviso === '' || d.aviso == null ? '' : Number(d.aviso), 'Pendiente', d.notas || '']);
  } finally {
    lock.releaseLock();
  }
  return datosWeb();
}

function cambiarEstado(id, estado, clave) {
  validarClave_(clave);
  if (ESTADOS.indexOf(estado) < 0) throw new Error('Estado inválido');
  const t = leerTareas_().find(x => String(x.id) === String(id));
  if (!t) throw new Error('No se encontró la tarea N° ' + id);
  hojaTareas_().getRange(t.fila, COL.ESTADO).setValue(estado);
  return datosWeb();
}
