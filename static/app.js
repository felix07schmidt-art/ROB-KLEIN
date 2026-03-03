let currentConfig = null;

async function fetchConfig() {
  const res = await fetch('/api/config');
  currentConfig = await res.json();
  await renderTabs();
}

async function renderTabs() {
  renderControl();
  renderSettings();
  await renderNetwork();
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
    </div>
  `;
}

function renderSettings() {
  const root = document.getElementById('settingsAxes');
  root.innerHTML = currentConfig.axes.map(axisSettingsBlock).join('');
}

async function renderNetwork() {
  const n = currentConfig.network;
  const netRes = await fetch('/api/network_status');
  const status = await netRes.json();
  const ethUrl = status.urls.eth0 || 'nicht verbunden';
  const wlanUrl = status.urls.wlan0 || 'nicht verbunden';

  document.getElementById('networkData').innerHTML = `
    <div class="axis-card">
      <p><strong>SSID:</strong> ${n.ap_ssid}</p>
      <p><strong>Passwort:</strong> ${n.ap_password}</p>
      <p><strong>Ethernet (eth0):</strong> ${ethUrl}</p>
      <p><strong>WLAN (wlan0):</strong> ${wlanUrl}</p>
      <p><strong>Listen-Host:</strong> ${status.listen_host}:${status.listen_port}</p>
    </div>
  `;
}

async function moveAxis(axis_id, target_deg) {
  const res = await fetch('/api/move', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ axis_id, target_deg })
  });
  const data = await res.json();
  const result = data.result;
  const axis = currentConfig.axes.find(a => a.id === axis_id);
  axis.current_deg = result.current_deg;
  document.getElementById(`actual-${axis_id}`).textContent = result.current_deg;
  document.getElementById(`slider-${axis_id}`).value = result.current_deg;
  document.getElementById(`input-${axis_id}`).value = result.current_deg;
}

async function moveAll() {
  const targets = currentConfig.axes.map(axis => ({
    axis_id: axis.id,
    target_deg: Number(document.getElementById(`input-${axis.id}`).value)
  }));

  const res = await fetch('/api/move_all', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ targets })
  });

  const data = await res.json();
  data.results.forEach(result => {
    const axis = currentConfig.axes.find(a => a.id === result.axis_id);
    axis.current_deg = result.current_deg;
    document.getElementById(`actual-${result.axis_id}`).textContent = result.current_deg;
    document.getElementById(`slider-${result.axis_id}`).value = result.current_deg;
    document.getElementById(`input-${result.axis_id}`).value = result.current_deg;
  });
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
    current_deg: Number(form[`current_deg-${axis.id}`].value)
  }));

  await fetch('/api/config', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ axes })
  });

  await fetchConfig();
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

document.getElementById('moveAllBtn').addEventListener('click', moveAll);
document.getElementById('settingsForm').addEventListener('submit', saveSettings);
installTabs();
fetchConfig();
