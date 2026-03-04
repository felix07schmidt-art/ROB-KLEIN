let currentConfig = null;
let consoleTimer = null;

function setStatus(text) {
  document.getElementById('statusBadge').textContent = `Status: ${text}`;
}

function logLocal(message) {
  const box = document.getElementById('consoleOutput');
  box.textContent += `[UI] ${message}\n`;
  box.scrollTop = box.scrollHeight;
}

async function fetchConfig() {
  const res = await fetch('/api/config');
  currentConfig = await res.json();
  renderTabs();
}

function renderTabs() {
  renderControl();
  renderPoints();
  renderSettings();
  renderNetwork();
}

function renderControl() {
  const root = document.getElementById('controlAxes');
  root.innerHTML = '';

  currentConfig.axes.forEach(axis => {
    const card = document.createElement('div');
    card.className = 'axis-card';

    card.innerHTML = `
      <div class="axis-row">
        <strong>${axis.name}</strong>
        <input type="range" min="${axis.min_deg}" max="${axis.max_deg}" step="0.1" value="${axis.current_deg}" id="slider-${axis.id}">
        <input type="number" min="${axis.min_deg}" max="${axis.max_deg}" step="0.1" value="${axis.current_deg}" id="input-${axis.id}">
        <button class="small-btn" data-axis-move="${axis.id}">Fahren</button>
      </div>
      <div class="step-buttons">
        <button class="small-btn" data-axis-step="${axis.id}" data-step="-10">-10°</button>
        <button class="small-btn" data-axis-step="${axis.id}" data-step="-5">-5°</button>
        <button class="small-btn" data-axis-step="${axis.id}" data-step="-1">-1°</button>
        <button class="small-btn" data-axis-step="${axis.id}" data-step="1">+1°</button>
        <button class="small-btn" data-axis-step="${axis.id}" data-step="5">+5°</button>
        <button class="small-btn" data-axis-step="${axis.id}" data-step="10">+10°</button>
      </div>
      <small>Grenzen: ${axis.min_deg}° bis ${axis.max_deg}° | Aktuell: <span id="actual-${axis.id}">${axis.current_deg}</span>°</small>
    `;

    root.appendChild(card);

    const slider = card.querySelector(`#slider-${axis.id}`);
    const input = card.querySelector(`#input-${axis.id}`);
    slider.addEventListener('input', () => { input.value = slider.value; });
    input.addEventListener('input', () => { slider.value = input.value; });
  });

  document.querySelectorAll('[data-axis-move]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const axisId = Number(btn.getAttribute('data-axis-move'));
      const target = Number(document.getElementById(`input-${axisId}`).value);
      await moveAxis(axisId, target);
    });
  });

  document.querySelectorAll('[data-axis-step]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const axisId = Number(btn.getAttribute('data-axis-step'));
      const delta = Number(btn.getAttribute('data-step'));
      const axis = currentConfig.axes.find(a => a.id === axisId);
      await moveAxis(axisId, axis.current_deg + delta);
    });
  });
}

function axisSettingsBlock(axis) {
  return `
    <div class="axis-card">
      <h3>${axis.name}</h3>
      <div class="axis-row"><label>Name</label><input type="text" name="name-${axis.id}" value="${axis.name}"><span></span><span></span></div>
      <div class="axis-row"><label>Min °</label><input type="number" step="0.1" name="min_deg-${axis.id}" value="${axis.min_deg}"><label>Max °</label><input type="number" step="0.1" name="max_deg-${axis.id}" value="${axis.max_deg}"></div>
      <div class="axis-row"><label>Steps / 90°</label><input type="number" name="steps_per_90_deg-${axis.id}" value="${axis.steps_per_90_deg}"><label>Aktuell °</label><input type="number" step="0.1" name="current_deg-${axis.id}" value="${axis.current_deg}"></div>
      <div class="axis-row"><label>Tempo (Steps/s)</label><input type="number" name="max_speed_steps_s-${axis.id}" value="${axis.max_speed_steps_s}"><label>Beschl. (Steps/s²)</label><input type="number" name="accel_steps_s2-${axis.id}" value="${axis.accel_steps_s2}"></div>
      <div class="axis-row"><label>STEP Pin</label><input type="number" name="step_pin-${axis.id}" value="${axis.step_pin}"><label>DIR Pin</label><input type="number" name="dir_pin-${axis.id}" value="${axis.dir_pin}"></div>
      <div class="axis-row"><label>ENABLE Pin</label><input type="number" name="enable_pin-${axis.id}" value="${axis.enable_pin || 0}"><span></span><span></span></div>
    </div>
  `;
}

function renderSettings() {
  const root = document.getElementById('settingsAxes');
  root.innerHTML = currentConfig.axes.map(axisSettingsBlock).join('');
}

function renderPoints() {
  const list = document.getElementById('pointsList');
  const points = currentConfig.points || [];
  if (!points.length) {
    list.innerHTML = '<p>Noch keine Points gespeichert.</p>';
    return;
  }

  list.innerHTML = points.map(point => `
    <div class="point-row">
      <strong>${point.name}</strong>
      <div>
        <button class="small-btn" data-point-move="${point.name}">Anfahren</button>
        <button class="small-btn danger" data-point-delete="${point.name}">Löschen</button>
      </div>
    </div>
  `).join('');

  document.querySelectorAll('[data-point-move]').forEach(btn => {
    btn.addEventListener('click', async () => movePoint(btn.getAttribute('data-point-move')));
  });
  document.querySelectorAll('[data-point-delete]').forEach(btn => {
    btn.addEventListener('click', async () => deletePoint(btn.getAttribute('data-point-delete')));
  });
}

async function renderNetwork() {
  const n = currentConfig.network;
  let networkStatus = null;
  try {
    const res = await fetch('/api/network_status');
    if (res.ok) {
      networkStatus = await res.json();
    }
  } catch (_) {
    networkStatus = null;
  }

  const preferredUrl = networkStatus?.preferred_url || `http://${n.preferred_ip || '192.168.100.2'}:${n.port}`;
  const reachableUrls = (networkStatus?.interfaces || []).map(
    i => `<li><code>http://${i.ip}:${n.port}</code> (${i.interface})</li>`
  ).join('');

  document.getElementById('networkData').innerHTML = `
    <div class="axis-card">
      <p><strong>Konfig. WLAN SSID:</strong> ${n.wifi_ssid || n.ap_ssid}</p>
      <p><strong>Konfig. WLAN Passwort:</strong> ${n.wifi_password || n.ap_password}</p>
      <p><strong>WLAN Interface:</strong> ${networkStatus?.wifi_interface || 'nicht erkannt'}</p>
      <p><strong>Aktiv verbundenes WLAN:</strong> ${networkStatus?.wifi_ssid_active || 'nicht verbunden / unbekannt'}</p>
      <p><strong>WLAN verbunden:</strong> ${networkStatus?.wifi_connected ? 'Ja' : 'Nein'}</p>
      <p><strong>Server-Binding:</strong> http://${n.host}:${n.port}</p>
      <p><strong>Bevorzugte URL:</strong> <code>${preferredUrl}</code></p>
      <p><strong>Erkannte LAN/WLAN-URLs:</strong></p>
      ${reachableUrls ? `<ul>${reachableUrls}</ul>` : '<p>Keine aktiven LAN/WLAN-Interfaces erkannt.</p>'}
    </div>
  `;
}

async function apiPost(url, body = {}) {
  const res = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (!res.ok || data.status === 'error') {
    throw new Error(data.message || 'API-Fehler');
  }
  return data;
}

function applyAxisResult(result) {
  const axis = currentConfig.axes.find(a => a.id === result.axis_id);
  axis.current_deg = result.current_deg;
  const actual = document.getElementById(`actual-${result.axis_id}`);
  const slider = document.getElementById(`slider-${result.axis_id}`);
  const input = document.getElementById(`input-${result.axis_id}`);
  if (actual) actual.textContent = result.current_deg;
  if (slider) slider.value = result.current_deg;
  if (input) input.value = result.current_deg;
}

async function moveAxis(axis_id, target_deg) {
  const data = await apiPost('/api/move', { axis_id, target_deg });
  applyAxisResult(data.result);
}

async function moveAll() {
  const targets = currentConfig.axes.map(axis => ({
    axis_id: axis.id,
    target_deg: Number(document.getElementById(`input-${axis.id}`).value)
  }));

  const data = await apiPost('/api/move_all', { targets });
  data.results.forEach(applyAxisResult);
}

async function saveSettings(e) {
  e.preventDefault();
  const form = e.target;
  const axes = currentConfig.axes.map(axis => ({
    id: axis.id,
    name: form[`name-${axis.id}`].value,
    min_deg: Number(form[`min_deg-${axis.id}`].value),
    max_deg: Number(form[`max_deg-${axis.id}`].value),
    steps_per_90_deg: Number(form[`steps_per_90_deg-${axis.id}`].value),
    max_speed_steps_s: Number(form[`max_speed_steps_s-${axis.id}`].value),
    accel_steps_s2: Number(form[`accel_steps_s2-${axis.id}`].value),
    step_pin: Number(form[`step_pin-${axis.id}`].value),
    dir_pin: Number(form[`dir_pin-${axis.id}`].value),
    enable_pin: Number(form[`enable_pin-${axis.id}`].value),
    current_deg: Number(form[`current_deg-${axis.id}`].value)
  }));

  await apiPost('/api/config', { axes });
  await fetchConfig();
  logLocal('Einstellungen gespeichert.');
}

async function emergencyStop() {
  await apiPost('/api/stop');
  setStatus('NOT-STOPP aktiv');
}

async function setEnable(enabled) {
  await apiPost('/api/enable', { enabled });
  setStatus(enabled ? 'Enable AN' : 'Enable AUS');
}

async function homeAll() {
  await apiPost('/api/home');
  currentConfig.axes.forEach(axis => {
    axis.current_deg = 0;
    const actual = document.getElementById(`actual-${axis.id}`);
    const slider = document.getElementById(`slider-${axis.id}`);
    const input = document.getElementById(`input-${axis.id}`);
    if (actual) actual.textContent = 0;
    if (slider) slider.value = 0;
    if (input) input.value = 0;
  });
  setStatus('Referenzfahrt fertig');
}

async function savePoint() {
  const name = document.getElementById('pointName').value.trim();
  if (!name) return;
  const data = await apiPost('/api/points', { name });
  currentConfig.points = data.points;
  renderPoints();
  document.getElementById('pointName').value = '';
}

async function movePoint(name) {
  const data = await apiPost('/api/points/move', { name });
  data.results.forEach(applyAxisResult);
}

async function deletePoint(name) {
  const res = await fetch(`/api/points?name=${encodeURIComponent(name)}`, { method: 'DELETE' });
  const data = await res.json();
  currentConfig.points = data.points;
  renderPoints();
}

async function refreshConsole() {
  const res = await fetch('/api/logs');
  const data = await res.json();
  const lines = data.logs.map(entry => `[${entry.ts}] ${entry.message}`).join('\n');
  const box = document.getElementById('consoleOutput');
  box.textContent = lines;
  box.scrollTop = box.scrollHeight;
  if (data.stop_active) {
    setStatus('NOT-STOPP aktiv');
  } else {
    setStatus(data.motors_enabled ? 'Enable AN' : 'Enable AUS');
  }
}

function installTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(x => x.classList.remove('active'));
      btn.classList.add('active');
      const tabId = btn.getAttribute('data-tab');
      document.getElementById(tabId).classList.add('active');
    });
  });
}

document.getElementById('moveAllBtn').addEventListener('click', () => moveAll().catch(e => alert(e.message)));
document.getElementById('settingsForm').addEventListener('submit', e => saveSettings(e).catch(err => alert(err.message)));
document.getElementById('stopBtn').addEventListener('click', () => emergencyStop().catch(e => alert(e.message)));
document.getElementById('enableBtn').addEventListener('click', () => setEnable(true).catch(e => alert(e.message)));
document.getElementById('disableBtn').addEventListener('click', () => setEnable(false).catch(e => alert(e.message)));
document.getElementById('homeBtn').addEventListener('click', () => homeAll().catch(e => alert(e.message)));
document.getElementById('savePointBtn').addEventListener('click', () => savePoint().catch(e => alert(e.message)));

installTabs();
fetchConfig();
refreshConsole();
consoleTimer = setInterval(refreshConsole, 2000);
