const $ = (id) => document.getElementById(id);

async function api(path, method = "GET", body) {
  const opt = { method };
  if (body !== undefined) {
    opt.headers = { "Content-Type": "application/json" };
    opt.body = JSON.stringify(body);
  }
  const r = await fetch(path, opt);
  return r.json();
}

// Live preview over WebSocket (falls back to polling the PNG).
function connectPreview() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  let ws;
  try {
    ws = new WebSocket(`${proto}://${location.host}/ws/preview`);
  } catch (e) {
    setInterval(() => { $("screen").src = "/preview.png?t=" + Date.now(); }, 200);
    return;
  }
  ws.onmessage = (ev) => { $("screen").src = ev.data; };
  ws.onclose = () => setTimeout(connectPreview, 1500);
}

async function refreshStatus() {
  try {
    const s = await api("/api/status");
    $("status").textContent = `${s.backend} · ${s.size[0]}×${s.size[1]} · ${s.enabled ? "on" : "off"}`;
    $("brightness").value = s.brightness;
    $("brightval").textContent = s.brightness;
    $("power").classList.toggle("active", s.enabled);
    document.querySelectorAll(".applet-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.key === s.current);
    });
  } catch (e) {
    $("status").textContent = "offline";
  }
}

async function loadApplets() {
  const list = await api("/api/applets");
  const box = $("applets");
  box.innerHTML = "";
  for (const a of list) {
    const b = document.createElement("button");
    b.className = "applet-btn";
    b.dataset.key = a.key;
    b.textContent = a.name;
    b.title = a.description || "";
    b.onclick = async () => { await api("/api/pin", "POST", { key: a.key }); refreshStatus(); };
    box.appendChild(b);
  }
}

$("power").onclick = async () => {
  const s = await api("/api/status");
  await api("/api/power", "POST", { on: !s.enabled });
  refreshStatus();
};

$("brightness").oninput = (e) => { $("brightval").textContent = e.target.value; };
$("brightness").onchange = async (e) => { await api("/api/brightness", "POST", { value: +e.target.value }); };

$("resume").onclick = async () => { await api("/api/resume", "POST", {}); refreshStatus(); };

$("file").onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append("file", f);
  await fetch("/api/upload", { method: "POST", body: fd });
  refreshStatus();
};

loadApplets();
connectPreview();
refreshStatus();
setInterval(refreshStatus, 3000);
