const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

async function api(path, method = "GET", body) {
  const o = { method };
  if (body !== undefined) { o.headers = { "Content-Type": "application/json" }; o.body = JSON.stringify(body); }
  const r = await fetch(path, o);
  return r.json();
}

/* ---- icons ---- */
const ICONS = {
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  sysmon: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6v6H9z"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3"/>',
  nowplaying: '<circle cx="7" cy="17" r="3"/><circle cx="18" cy="15" r="3"/><path d="M10 17V5l11-2v12"/>',
  vumeter: '<path d="M4 14v4M8 9v9M12 4v14M16 9v9M20 14v4"/>',
  player: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>',
  text: '<path d="M4 6h16M9 6v12M15 6v12"/>',
  weather: '<path d="M7 17a4 4 0 010-8 5 5 0 019.6 1.5A3.5 3.5 0 0117 17z"/>',
  _: '<rect x="4" y="4" width="16" height="16" rx="3"/>',
};
const icon = (k) => `<svg class="ti" viewBox="0 0 24 24">${ICONS[k] || ICONS._}</svg>`;

/* ---- live preview (poll, double-buffered) ---- */
function startPreview() {
  const img = $("#screen");
  setInterval(() => {
    const p = new Image();
    p.onload = () => { img.src = p.src; };
    p.src = "/preview.png?t=" + Date.now();
  }, 80);
}

/* ---- status ---- */
let APPLETS = [];
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    $("#status").textContent = `${s.backend} · ${s.enabled ? "on" : "off"}`;
    $("#power").classList.toggle("on", s.enabled);
    $("#brightness").value = s.brightness; $("#brightval").textContent = s.brightness;
    $$(".tile").forEach((t) => t.classList.toggle("active", t.dataset.key === s.current));
    renderPlaylist(s.playlist);
  } catch (e) { $("#status").textContent = "offline"; }
}

async function loadApplets() {
  APPLETS = await api("/api/applets");
  const grid = $("#applets"); grid.innerHTML = "";
  for (const a of APPLETS) {
    const t = document.createElement("div");
    t.className = "tile"; t.dataset.key = a.key;
    const hasCfg = a.config_schema && Object.keys(a.config_schema).length;
    t.innerHTML = icon(a.key) + `<h3>${a.name}</h3><p>${a.description || ""}</p>` +
      (hasCfg ? '<span class="gear">⚙</span>' : "");
    t.onclick = async (e) => {
      if (e.target.classList.contains("gear")) return openDrawer(a);
      await api("/api/pin", "POST", { key: a.key }); refreshStatus();
    };
    grid.appendChild(t);
  }
}

/* ---- settings drawer ---- */
let drawerApplet = null;
function openDrawer(a) {
  drawerApplet = a;
  $("#drawer-title").textContent = a.name;
  const box = $("#drawer-fields"); box.innerHTML = "";
  for (const [key, spec] of Object.entries(a.config_schema || {})) {
    const wrap = document.createElement("div");
    const lab = spec.label || key;
    if (spec.type === "bool") {
      wrap.className = "field bool";
      wrap.innerHTML = `<input type="checkbox" id="f_${key}" ${spec.default ? "checked" : ""}><label for="f_${key}">${lab}</label>`;
    } else {
      const t = spec.type === "int" ? "number" : "text";
      wrap.className = "field";
      wrap.innerHTML = `<label>${lab}</label><input type="${t}" id="f_${key}" value="${spec.default ?? ""}">`;
    }
    box.appendChild(wrap);
  }
  $("#drawer").classList.add("open");
}
$("#drawer-close").onclick = () => $("#drawer").classList.remove("open");
$("#drawer").onclick = (e) => { if (e.target.id === "drawer") $("#drawer").classList.remove("open"); };
$("#drawer-apply").onclick = async () => {
  const cfg = {};
  for (const [key, spec] of Object.entries(drawerApplet.config_schema || {})) {
    const el = $(`#f_${key}`); if (!el) continue;
    cfg[key] = spec.type === "bool" ? el.checked : (spec.type === "int" ? +el.value : el.value);
  }
  await api("/api/pin", "POST", { key: drawerApplet.key, config: cfg });
  $("#drawer").classList.remove("open"); refreshStatus();
};

/* ---- controls ---- */
$("#power").onclick = async () => { const s = await api("/api/status"); await api("/api/power", "POST", { on: !s.enabled }); refreshStatus(); };
$("#brightness").oninput = (e) => { $("#brightval").textContent = e.target.value; };
$("#brightness").onchange = (e) => api("/api/brightness", "POST", { value: +e.target.value });
$("#resume").onclick = async () => { await api("/api/resume", "POST", {}); refreshStatus(); };
$("#pl-resume").onclick = $("#resume").onclick;

/* ---- tabs ---- */
$$(".tab").forEach((b) => b.onclick = () => {
  $$(".tab").forEach((x) => x.classList.remove("active"));
  $$(".panel-view").forEach((x) => x.classList.remove("active"));
  b.classList.add("active"); $("#tab-" + b.dataset.tab).classList.add("active");
});

/* ---- playlist ---- */
function renderPlaylist(pl) {
  const box = $("#playlist"); if (!box) return; box.innerHTML = "";
  (pl || []).forEach((it, i) => {
    const row = document.createElement("div");
    row.className = "prow";
    row.innerHTML = `<span class="name">${it.applet}</span><input type="number" min="2" value="${it.duration}"> <span class="dim">s</span>`;
    row.querySelector("input").onchange = async (e) => {
      pl[i].duration = +e.target.value; await api("/api/playlist", "POST", { playlist: pl });
    };
    box.appendChild(row);
  });
}

/* ---- files ---- */
const drop = $("#drop");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => uploadFile(e.dataTransfer.files[0]));
$("#file").onchange = (e) => uploadFile(e.target.files[0]);
async function uploadFile(f) {
  if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  await fetch("/api/upload", { method: "POST", body: fd }); refreshStatus();
}

/* ---- editor ---- */
const pad = $("#pad"), pctx = pad.getContext("2d");
pctx.imageSmoothingEnabled = false;
let frames = [blankFrame()], cur = 0, tool = "pen", drawing = false, playTimer = null;
function blankFrame() { const c = document.createElement("canvas"); c.width = 256; c.height = 64; const x = c.getContext("2d"); x.fillStyle = "#000"; x.fillRect(0, 0, 256, 64); return c.toDataURL(); }
function loadCur() { const im = new Image(); im.onload = () => { pctx.clearRect(0, 0, 256, 64); pctx.drawImage(im, 0, 0); }; im.src = frames[cur]; }
function saveCur() { frames[cur] = pad.toDataURL(); drawStrip(); }
let lastP = null, penActive = false;
function padXY(e) { const r = pad.getBoundingClientRect();
  return [(e.clientX - r.left) * 256 / r.width, (e.clientY - r.top) * 64 / r.height]; }
function brushColor(e) {
  if (tool === "erase") return "#000";
  if (e.pointerType === "pen") {              // pressure -> grayscale shade (16-level panel)
    const g = Math.max(70, Math.min(255, Math.round(70 + 185 * (e.pressure || 0.4))));
    return `rgb(${g},${g},${g})`;
  }
  return "#fff";
}
function stamp(x, y, b, color) { pctx.fillStyle = color; pctx.fillRect(Math.round(x) - (b >> 1), Math.round(y) - (b >> 1), b, b); }
function strokeTo(e) {
  const b = +$("#brush").value, color = brushColor(e), [x, y] = padXY(e);
  if (lastP) {                                 // interpolate so fast strokes have no gaps
    const dx = x - lastP[0], dy = y - lastP[1], steps = Math.max(1, Math.ceil(Math.hypot(dx, dy)));
    for (let i = 1; i <= steps; i++) stamp(lastP[0] + dx * i / steps, lastP[1] + dy * i / steps, b, color);
  } else stamp(x, y, b, color);
  lastP = [x, y];
}
pad.addEventListener("pointerdown", (e) => {
  if (e.pointerType === "touch" && penActive) return;   // palm rejection
  if (e.pointerType === "pen") penActive = true;
  drawing = true; lastP = null; pad.setPointerCapture(e.pointerId); strokeTo(e); e.preventDefault();
});
pad.addEventListener("pointermove", (e) => { if (drawing) { strokeTo(e); e.preventDefault(); } });
function endStroke(e) { if (drawing) { drawing = false; lastP = null; saveCur(); } if (e && e.pointerType === "pen") penActive = false; }
pad.addEventListener("pointerup", endStroke);
pad.addEventListener("pointercancel", endStroke);
$$(".tool").forEach((b) => b.onclick = () => { tool = b.dataset.tool; $$(".tool").forEach((x) => x.classList.remove("active")); b.classList.add("active"); });
$("#clear").onclick = () => { pctx.fillStyle = "#000"; pctx.fillRect(0, 0, 256, 64); saveCur(); };
$("#invert").onclick = () => { const d = pctx.getImageData(0, 0, 256, 64); for (let i = 0; i < d.data.length; i += 4) { d.data[i] = d.data[i + 1] = d.data[i + 2] = 255 - d.data[i]; } pctx.putImageData(d, 0, 0); saveCur(); };
$("#frame-add").onclick = () => { frames.splice(cur + 1, 0, blankFrame()); cur++; loadCur(); drawStrip(); };
$("#frame-dup").onclick = () => { frames.splice(cur + 1, 0, frames[cur]); cur++; loadCur(); drawStrip(); };
$("#frame-del").onclick = () => { if (frames.length > 1) { frames.splice(cur, 1); cur = Math.max(0, cur - 1); loadCur(); drawStrip(); } };
function drawStrip() {
  const strip = $("#filmstrip"); strip.innerHTML = "";
  frames.forEach((f, i) => {
    const c = document.createElement("canvas"); c.width = 256; c.height = 64;
    if (i === cur) c.classList.add("active");
    const im = new Image(); im.onload = () => c.getContext("2d").drawImage(im, 0, 0); im.src = f;
    c.onclick = () => { saveCur(); cur = i; loadCur(); drawStrip(); };
    strip.appendChild(c);
  });
}
$("#play").onclick = (e) => {
  if (playTimer) { clearInterval(playTimer); playTimer = null; e.target.textContent = "▶ preview"; return; }
  e.target.textContent = "■ stop"; let i = 0;
  playTimer = setInterval(() => { const im = new Image(); im.onload = () => { pctx.clearRect(0, 0, 256, 64); pctx.drawImage(im, 0, 0); }; im.src = frames[i % frames.length]; i++; }, 1000 / (+$("#efps").value || 12));
};
$("#send").onclick = async () => { saveCur(); await api("/api/draw", "POST", { frames }); refreshStatus(); };

/* ---- layout (zones) ---- */
async function loadLayouts() {
  const box = $("#layouts"); if (!box) return;
  const presets = await api("/api/layouts");
  box.innerHTML = "";
  for (const p of presets) {
    const t = document.createElement("div");
    t.className = "tile";
    const parts = p.zones.map((z) => z.applet).join(" · ");
    t.innerHTML = `<h3>${p.name}</h3><p>${parts}</p>`;
    t.onclick = async () => { await api("/api/layout", "POST", { zones: p.zones }); refreshStatus(); };
    box.appendChild(t);
  }
}
function fillZoneSelects() {
  const opts = APPLETS.filter((a) => a.key !== "player").map((a) => `<option value="${a.key}">${a.name}</option>`).join("");
  const L = $("#z-left"), R = $("#z-right");
  if (!L || !R) return;
  L.innerHTML = opts; R.innerHTML = opts;
  L.value = "logo"; R.value = "vumeter";
}
const applySplit = $("#apply-split");
if (applySplit) applySplit.onclick = async () => {
  const lw = Math.round(256 * (+$("#split").value) / 100);
  const zones = [
    { applet: $("#z-left").value, box: [0, 0, lw, 64] },
    { applet: $("#z-right").value, box: [lw, 0, 256 - lw, 64] },
  ];
  await api("/api/layout", "POST", { zones }); refreshStatus();
};

/* ---- boot ---- */
loadCur(); drawStrip(); startPreview();
loadApplets().then(() => { fillZoneSelects(); refreshStatus(); });
loadLayouts();
setInterval(refreshStatus, 3000);
