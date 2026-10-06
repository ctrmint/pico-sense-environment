'use strict';
const $ = id => document.getElementById(id);
const number = (v, digits = 1) => typeof v === 'number' && Number.isFinite(v) ? v.toFixed(digits) : '--';
let history = {fields: [], rows: []};
let polls = 0;
let lastSuccess = null;

async function getJSON(path) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 7000);
  try {
    const response = await fetch(path, {cache: 'no-store', signal: controller.signal});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return await response.json();
  } finally { clearTimeout(timer); }
}

function renderStatus(s) {
  const r = s.readings;
  $('name').textContent = s.device_name;
  document.title = s.device_name;
  $('temperature').textContent = number(r.temperature_c);
  $('humidity').textContent = number(r.humidity_pct);
  $('pressure').textContent = number(r.pressure_hpa);
  $('gas').textContent = number(r.voc_raw, 0);
  $('light').textContent = number(r.light_raw, 0);
  $('rgb').textContent = r.rgb ? `R ${r.rgb.r} / G ${r.rgb.g} / B ${r.rgb.b}` : 'R -- / G -- / B --';
  $('gain').textContent = r.light_gain == null ? 'Sensor unavailable' : `${r.light_gain}× gain · ${number(r.light_integration_ms)} ms integration${r.light_saturated ? ' · SATURATED' : ''}`;
  $('connection').textContent = 'Connected';
  $('connection').className = 'badge ok';
  $('alerts').replaceChildren();
  const alerts = s.alerts.slice();
  if (s.services.display === 'error') alerts.push('LCD unavailable');
  if (s.services.mqtt === 'retrying') alerts.push('MQTT broker unavailable');
  if (!alerts.length) alerts.push('All sensors reporting. No threshold advisories.');
  for (const text of alerts) { const li = document.createElement('li'); li.textContent = text; $('alerts').append(li); }
  $('device').replaceChildren();
  const details = {'Device ID': s.device_id, 'IP address': s.wifi.ip || '--',
    'Wi-Fi signal': s.wifi.rssi == null ? '--' : s.wifi.rssi + ' dBm',
    'Uptime': Math.floor(s.uptime_s / 3600) + 'h ' + Math.floor(s.uptime_s % 3600 / 60) + 'm',
    'Gas compensation': s.gas_compensation === 'sht31' ? 'Live SHT31 temperature / humidity' : 'Default 25 °C / 50% RH',
    'BME temperature': number(r.bme_temperature_c) + ' °C',
    'BME humidity': number(r.bme_humidity_pct) + ' %',
    'Free memory': Math.round(s.free_heap_bytes / 1024) + ' KiB',
    'MQTT': s.services.mqtt, 'Firmware': s.firmware_version};
  for (const [label, value] of Object.entries(details)) {
    const dt = document.createElement('dt'); dt.textContent = label;
    const dd = document.createElement('dd'); dd.textContent = value; $('device').append(dt, dd);
  }
  $('sensors').replaceChildren();
  for (const [name, info] of Object.entries(s.sensors)) {
    const tr = document.createElement('tr');
    for (const value of [name.toUpperCase(), info.status, info.age_s == null ? '--' : info.age_s + ' s']) {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    }
    if (info.error) tr.title = info.error;
    $('sensors').append(tr);
  }
  $('history-info').textContent = `${s.history.count} of ${s.history.capacity} samples · one every ${s.history.interval_s}s · RAM history resets at reboot.`;
  lastSuccess = new Date();
  $('updated').textContent = 'Last received ' + lastSuccess.toLocaleTimeString() + ' · refreshes every 5 seconds';
}

function drawHistory() {
  const canvas = $('chart');
  const width = canvas.clientWidth || 300, height = 220, ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio); ctx.clearRect(0, 0, width, height);
  const ti = history.fields.indexOf('temperature_c');
  const ui = history.fields.indexOf('uptime_s');
  const rows = history.rows;
  const values = rows.map(r => r[ti]).filter(v => typeof v === 'number' && Number.isFinite(v));
  ctx.font = '12px system-ui'; ctx.fillStyle = '#93a9ba';
  if (values.length < 2) { ctx.fillText('Waiting for two temperature samples...', 12, 100); return; }
  let low = Math.min(...values), high = Math.max(...values);
  if (high - low < 2) { const mid = (high + low) / 2; low = mid - 1; high = mid + 1; }
  const left = 48, right = width - 12, top = 18, bottom = height - 28;
  const first = rows[0][ui], last = rows[rows.length - 1][ui];
  if (last <= first) return;
  for (let n = 0; n <= 4; n++) {
    const y = top + (bottom - top) * n / 4;
    ctx.strokeStyle = '#26394a'; ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
    ctx.fillText((high - (high - low) * n / 4).toFixed(1), 4, y + 4);
  }
  ctx.fillText('°C', 5, 12); ctx.fillText('-' + Math.round((last - first) / 60) + ' min', left, height - 5);
  ctx.fillText('latest', Math.max(left, right - 34), height - 5);
  ctx.strokeStyle = '#59d9bc'; ctx.lineWidth = 2; ctx.beginPath();
  let drawing = false;
  for (const row of rows) {
    const value = row[ti];
    if (typeof value !== 'number' || !Number.isFinite(value)) { drawing = false; continue; }
    const x = left + (row[ui] - first) / (last - first) * (right - left);
    const y = bottom - (value - low) / (high - low) * (bottom - top);
    if (drawing) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    drawing = true;
  }
  ctx.stroke();
}

async function poll() {
  try {
    renderStatus(await getJSON('/api/status'));
    if (polls++ % 6 === 0) {
      try { history = await getJSON('/api/history'); drawHistory(); }
      catch (_) { $('history-info').textContent = 'History temporarily unavailable; current readings remain connected.'; }
    }
  } catch (_) {
    $('connection').textContent = 'Disconnected'; $('connection').className = 'badge error';
    for (const id of ['temperature', 'humidity', 'pressure', 'gas', 'light']) $(id).textContent = '--';
    $('rgb').textContent = 'R -- / G -- / B --';
    $('updated').textContent = 'Device unreachable. ' + (lastSuccess ? 'Last received ' + lastSuccess.toLocaleTimeString() + '.' : '') + ' Retrying...';
  } finally { setTimeout(poll, 5000); }
}
window.addEventListener('resize', drawHistory);
poll();
