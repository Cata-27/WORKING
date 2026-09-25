/**
 * Webhook de Google Sheets para la búsqueda de empleo.
 *
 * Instalación (una sola vez), desde la hoja de cálculo:
 *   1. Extensiones → Apps Script → pega este archivo completo en Code.gs.
 *   2. Configuración del proyecto (⚙️) → Propiedades del script → agrega:
 *        TOKEN = <una contraseña larga inventada; la misma que el secreto SHEETS_TOKEN>
 *   3. Ejecuta la función `configurar` una vez (menú ▶) y acepta los permisos.
 *   4. Implementar → Nueva implementación → Tipo: Aplicación web
 *        Ejecutar como: Yo      Quién tiene acceso: Cualquier persona
 *      Copia la URL (termina en /exec): es el secreto SHEETS_WEBHOOK_URL.
 */

const HOJA_OFERTAS = 'Ofertas';
const HOJA_ENLACES = 'Enlaces del día';
const HOJA_VISTOS = 'Vistos';
const ESTADOS = ['Nueva', 'Aplicada', 'Entrevista', 'Oferta', 'Rechazada', 'Descartada'];
const ENVIAR_CORREO = true;

function configurar() {
  const libro = SpreadsheetApp.getActiveSpreadsheet();
  hoja_(libro, HOJA_OFERTAS);
  hoja_(libro, HOJA_ENLACES);
  hoja_(libro, HOJA_VISTOS).hideSheet();
  if (!PropertiesService.getScriptProperties().getProperty('TOKEN')) {
    throw new Error('Falta la propiedad TOKEN en Configuración del proyecto → Propiedades del script');
  }
  Logger.log('Listo. Ahora implementa como aplicación web.');
}

function doGet(e) {
  if (!autorizado_(e.parameter.token)) return json_({ ok: false, error: 'token inválido' });
  if (e.parameter.accion === 'vistos') {
    const hoja = hoja_(SpreadsheetApp.getActiveSpreadsheet(), HOJA_VISTOS);
    const n = hoja.getLastRow();
    const ids = n ? hoja.getRange(1, 1, n, 1).getValues().map(r => String(r[0])) : [];
    return json_({ ok: true, ids: ids.concat(idsEnOfertas_()) });
  }
  if (e.parameter.accion === 'aplicadas') {
    return json_({ ok: true, filas: filasPorEstado_(['Aplicada', 'Entrevista']) });
  }
  return json_({ ok: true, mensaje: 'Webhook de búsqueda de empleo activo' });
}

function doPost(e) {
  let datos;
  try {
    datos = JSON.parse(e.postData.contents);
  } catch (err) {
    return json_({ ok: false, error: 'JSON inválido' });
  }
  if (!autorizado_(datos.token)) return json_({ ok: false, error: 'token inválido' });

  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const libro = SpreadsheetApp.getActiveSpreadsheet();
    const agregadas = agregarOfertas_(libro, datos.columnas || [], datos.filas || []);
    agregarVistos_(libro, datos.vistos || []);
    if (datos.enlaces && datos.enlaces.length) escribirEnlaces_(libro, datos.enlaces);
    if (ENVIAR_CORREO && agregadas.length) enviarResumen_(libro, agregadas, datos.enlaces || []);
    return json_({ ok: true, agregadas: agregadas.length });
  } finally {
    lock.releaseLock();
  }
}

// --- Helpers --------------------------------------------------------------

function autorizado_(token) {
  const esperado = PropertiesService.getScriptProperties().getProperty('TOKEN');
  return Boolean(esperado) && token === esperado;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function hoja_(libro, nombre) {
  return libro.getSheetByName(nombre) || libro.insertSheet(nombre);
}

function idsEnOfertas_() {
  const hoja = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(HOJA_OFERTAS);
  if (!hoja || hoja.getLastRow() < 2) return [];
  const encabezados = hoja.getRange(1, 1, 1, hoja.getLastColumn()).getValues()[0];
  const col = encabezados.indexOf('ID') + 1;
  if (!col) return [];
  return hoja.getRange(2, col, hoja.getLastRow() - 1, 1).getValues().map(r => String(r[0]));
}

function prepararEncabezados_(hoja, columnas) {
  if (hoja.getLastRow() > 0) return hoja.getRange(1, 1, 1, hoja.getLastColumn()).getValues()[0];
  hoja.appendRow(columnas);
  hoja.setFrozenRows(1);
  hoja.getRange(1, 1, 1, columnas.length).setFontWeight('bold').setBackground('#1f3a5f').setFontColor('#ffffff');
  const anchos = { 'Puesto': 260, 'Empresa': 160, 'Resumen': 280, 'Por qué encaja': 300, 'Riesgos': 240,
                   'Puntos a destacar': 300, 'Carta de presentación': 420, 'Mensaje corto': 300,
                   'Preguntas probables': 360, 'Enlace': 200, 'Notas': 220 };
  columnas.forEach((c, i) => { if (anchos[c]) hoja.setColumnWidth(i + 1, anchos[c]); });
  const colEstado = columnas.indexOf('Estado') + 1;
  if (colEstado) {
    const regla = SpreadsheetApp.newDataValidation().requireValueInList(ESTADOS, true).build();
    hoja.getRange(2, colEstado, hoja.getMaxRows() - 1, 1).setDataValidation(regla);
  }
  const colPuntaje = columnas.indexOf('Puntaje') + 1;
  if (colPuntaje) {
    const rango = hoja.getRange(2, colPuntaje, hoja.getMaxRows() - 1, 1);
    hoja.setConditionalFormatRules([
      SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThanOrEqualTo(75)
        .setBackground('#c8e6c9').setRanges([rango]).build(),
      SpreadsheetApp.newConditionalFormatRule().whenNumberBetween(55, 74)
        .setBackground('#fff9c4').setRanges([rango]).build(),
    ]);
  }
  return columnas;
}

function agregarOfertas_(libro, columnas, filas) {
  if (!filas.length) return [];
  const hoja = hoja_(libro, HOJA_OFERTAS);
  const encabezados = prepararEncabezados_(hoja, columnas);
  const existentes = new Set(idsEnOfertas_());
  const nuevas = filas.filter(f => !existentes.has(String(f['ID'])));
  if (!nuevas.length) return [];
  const valores = nuevas.map(f => encabezados.map(c => (f[c] === undefined ? '' : f[c])));
  const inicio = hoja.getLastRow() + 1;
  hoja.getRange(inicio, 1, valores.length, encabezados.length).setValues(valores)
    .setVerticalAlignment('top').setWrap(true);
  hoja.setRowHeights(inicio, valores.length, 60);
  return nuevas;
}

function agregarVistos_(libro, ids) {
  if (!ids.length) return;
  const hoja = hoja_(libro, HOJA_VISTOS);
  hoja.getRange(hoja.getLastRow() + 1, 1, ids.length, 1).setValues(ids.map(i => [i]));
}

function escribirEnlaces_(libro, enlaces) {
  const hoja = hoja_(libro, HOJA_ENLACES);
  hoja.clear();
  hoja.appendRow(['Portal', 'Búsqueda', 'Abrir']);
  hoja.getRange(1, 1, 1, 3).setFontWeight('bold');
  enlaces.forEach(e => hoja.appendRow([e.portal, e.descripcion, e.url]));
  hoja.setColumnWidth(2, 320);
}

function filasPorEstado_(estados) {
  const hoja = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(HOJA_OFERTAS);
  if (!hoja || hoja.getLastRow() < 2) return [];
  const datos = hoja.getDataRange().getValues();
  const enc = datos.shift();
  return datos
    .map(r => Object.fromEntries(enc.map((c, i) => [c, r[i] instanceof Date ? r[i].toISOString().slice(0, 10) : r[i]])))
    .filter(f => estados.indexOf(f['Estado']) >= 0)
    .map(f => ({ ID: f['ID'], Empresa: f['Empresa'], Puesto: f['Puesto'], Enlace: f['Enlace'],
                 Estado: f['Estado'], 'Fecha aplicación': f['Fecha aplicación'], Notas: f['Notas'] }));
}

function esc_(t) {
  return String(t === undefined || t === null ? '' : t)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function enviarResumen_(libro, filas, enlaces) {
  const destino = Session.getEffectiveUser().getEmail();
  if (!destino) return;
  const top = filas.slice(0, 10);
  const items = top.map(f =>
    `<li><b>${esc_(f['Puntaje'])}</b> · <a href="${esc_(f['Enlace'])}">${esc_(f['Puesto'])}</a> · ${esc_(f['Empresa'])}` +
    ` · ${esc_(f['Modalidad'])}${f['¿Startup?'] === 'Sí' ? ' · 🚀 startup' : ''}<br>` +
    `<small>${esc_(f['Resumen'])}</small></li>`).join('');
  const links = enlaces.slice(0, 6).map(e => `<li><a href="${esc_(e.url)}">${esc_(e.portal)}: ${esc_(e.descripcion)}</a></li>`).join('');
  MailApp.sendEmail({
    to: destino,
    subject: `💼 ${filas.length} ofertas nuevas listas para aplicar`,
    htmlBody:
      `<p>Hola Ana, hoy encontré <b>${filas.length}</b> ofertas que encajan contigo. ` +
      `Las cartas ya están listas en la <a href="${libro.getUrl()}">hoja</a>.</p><ol>${items}</ol>` +
      (links ? `<p>Búsquedas manuales del día (aplica desde tu cuenta):</p><ul>${links}</ul>` : '') +
      `<p>Cuando apliques, cambia el Estado a <b>Aplicada</b> y pon la fecha 🙌</p>`,
  });
}
