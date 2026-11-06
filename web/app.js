/* UC indoor navigation: Leaflet (CRS.Simple, 1 unit = 1 m) on top of the Flask API. */
const $ = (s, el = document) => el.querySelector(s);
const CATS = {
  lab: ["Lab", "ServerRoom"], class: ["Classroom", "Theater"], office: ["Office", "LecturerRoom", "MeetingRoom"],
  fnb: ["Pantry", "Lounge"], service: ["Toilet", "Clinic", "ATMRoom", "PrayerRoom", "Utility", "Storage"],
  library: ["Library"], transit: ["Lift", "Stairs"],
};
const CAT_NAME = { lab: "Labs", class: "Classrooms", office: "Offices", fnb: "Food & lounge", service: "Services", library: "Library", transit: "Lift / stairs" };
const catOf = t => Object.keys(CATS).find(k => CATS[k].includes(t)) || "other";
const TYPE_NAME = { LecturerRoom: "Lecturer room", MeetingRoom: "Meeting room", ServerRoom: "Server room", ATMRoom: "ATM", PrayerRoom: "Prayer room" };
const typeName = t => TYPE_NAME[t] || t;
const LANDMARKS = ["Lift", "Stairs", "Library", "Theater", "Lounge"];
const shortName = n => n.replace(/\s*\(.*?\)/g, "").replace(/\s+Lt\s*\w+$/, "");

const S = {
  floors: {}, order: [], rooms: [], roomByKey: {},
  me: { floor: "1", x: 50, y: 45 }, view: "1", step: 1, radius: 5,
  can: { up: false, down: false }, nearby: {}, trail: [], route: null, dest: null, seq: 0, busy: false,
};

const map = L.map("map", { crs: L.CRS.Simple, minZoom: -1, maxZoom: 6, zoomSnap: 0.25, zoomDelta: 0.5, attributionControl: false, zoomControl: false });
L.control.zoom({ position: "topright" }).addTo(map);
const layers = { base: L.layerGroup().addTo(map), labels: L.layerGroup().addTo(map), route: L.layerGroup().addTo(map), me: L.layerGroup().addTo(map) };
let roomLayers = {}, labelMarkers = [];

const api = (path, body) => fetch("/api/" + path, body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : {}).then(r => r.json());
const pos = () => ({ floor: S.me.floor, x: S.me.x, y: S.me.y, step: S.step, radius: S.radius });
const ll = (x, y) => [y, x];
const rect = b => [[b[1], b[0]], [b[3], b[2]]];
const roomDist = (b, x, y) => Math.hypot(Math.max(b[0] - x, 0, x - b[2]), Math.max(b[1] - y, 0, y - b[3]));

/* ---------- drawing a floor ---------- */
function drawFloor(name) {
  const F = S.floors[name];
  layers.base.clearLayers(); layers.labels.clearLayers(); roomLayers = {}; labelMarkers = [];
  F.outline_rects.forEach(r => L.rectangle(rect(r), { className: "floor", interactive: false }).addTo(layers.base));
  F.patches.forEach(p => L.rectangle(rect(p.bbox), { className: "room cat-" + catOf(p.type), interactive: false, weight: .8 }).addTo(layers.base));
  F.voids.forEach(v => {
    L.rectangle(rect(v), { className: "void", interactive: false }).addTo(layers.base);
    labelMarker((v[0] + v[2]) / 2, (v[1] + v[3]) / 2, [v[2] - v[0], v[3] - v[1]], "VOID", "VOID", false, true);
  });
  F.rooms.forEach(r => {
    const layer = L.rectangle(rect(r.bbox), { className: "room cat-" + catOf(r.type) }).addTo(layers.base);
    roomLayers[r.id] = layer;
    layer.bindTooltip(() => roomInfo(r, name), { sticky: true, direction: "top", opacity: 1 });
    layer.bindPopup(() => popup(r, name), { closeButton: false });
    const w = r.bbox[2] - r.bbox[0], h = r.bbox[3] - r.bbox[1];
    const link = r.type === "Lift" || r.type === "Stairs";
    let short, long;
    if (link) {
      const arrows = [r.links.up ? "↑" + r.links.up : "", r.links.down ? "↓" + r.links.down : ""].filter(Boolean);
      short = arrows.join(" ") || (r.type === "Lift" ? "Lift" : "Stairs");
      long = (r.type === "Lift" ? "Lift" : "Stairs") + "\n" + arrows.join(" ");
    } else { short = r.id; long = shortName(r.name); }
    labelMarker((r.bbox[0] + r.bbox[2]) / 2, (r.bbox[1] + r.bbox[3]) / 2, [w, h], short, long, link, LANDMARKS.includes(r.type));
  });
  markRoomClasses();
  updateLabels();
}

function labelMarker(x, y, size, short, long, link, landmark) {
  const m = L.marker(ll(x, y), { icon: L.divIcon({ className: "lbl" + (link ? " link" : ""), html: "<span></span>", iconSize: [0, 0] }), interactive: false, keyboard: false }).addTo(layers.labels);
  labelMarkers.push({ m, size, short, long, landmark });
}

/* zoom-dependent labels: landmarks first, other rooms only when they are big enough on screen */
function updateLabels() {
  const k = Math.pow(2, map.getZoom());
  labelMarkers.forEach(l => {
    const el = l.m.getElement(); if (!el) return;
    const pw = l.size[0] * k, ph = l.size[1] * k;
    const longLines = l.long.split("\n"), longW = Math.max(...longLines.map(s => s.length)) * 6;
    let text = "";
    if (pw >= longW + 6 && ph >= longLines.length * 13 + 4 && (l.landmark || k >= 7)) text = l.long;
    else if (pw >= l.short.length * 6.4 + 4 && ph >= 14 && (l.landmark || k >= 9)) text = l.short;
    const span = el.firstChild; if (span.textContent !== text) span.textContent = text;
  });
}
map.on("zoomend", updateLabels);
map.on("layeradd", e => { if (e.layer instanceof L.Marker) setTimeout(updateLabels, 0); });

function roomInfo(r, floor) {
  const d = floor === S.me.floor ? ` · ${roomDist(r.bbox, S.me.x, S.me.y).toFixed(1)} m from you` : "";
  return `<b>${r.name}</b><br>Lt ${floor} · ${typeName(r.type)}${d}`;
}
function popup(r, floor) {
  const div = document.createElement("div"); div.className = "pop"; div.innerHTML = roomInfo(r, floor) + '<br><button>Directions here</button>';
  div.querySelector("button").onclick = () => { map.closePopup(); setDest(S.roomByKey[floor + ":" + r.id]); };
  return div;
}

function markRoomClasses() {
  const F = S.floors[S.view];
  F.rooms.forEach(r => {
    const el = roomLayers[r.id]?.getElement(); if (!el) return;
    el.classList.toggle("near", S.view === S.me.floor && S.nearby[r.id] !== undefined);
    el.classList.toggle("target", !!S.dest && S.dest.floor === S.view && S.dest.id === r.id);
  });
}

/* ---------- user dot + buffer ---------- */
let meMarker, buffer, trailLine;
function drawMe() {
  layers.me.clearLayers();
  if (S.view !== S.me.floor) return;
  buffer = L.circle(ll(S.me.x, S.me.y), { radius: S.radius, color: "#3b6ef5", weight: 1.5, fillOpacity: .12, interactive: false }).addTo(layers.me);
  if (S.trail.length > 1) L.polyline(S.trail.map(p => ll(...p)), { className: "trail", interactive: false }).addTo(layers.me);
  meMarker = L.marker(ll(S.me.x, S.me.y), { icon: L.divIcon({ className: "", html: '<div class="me-dot"></div>', iconSize: [0, 0] }), zIndexOffset: 1000, interactive: false }).addTo(layers.me);
}

/* ---------- floor pill ---------- */
function drawFloors() {
  const onRoute = new Set((S.route?.segments || []).map(s => s.floor));
  $("#floors").innerHTML = '<div class="lt">LT</div>' + [...S.order].reverse().map(f =>
    `<button data-f="${f}" class="${f === S.view ? "on " : ""}${f === S.me.floor ? "me " : ""}${onRoute.has(f) ? "route" : ""}">${f}</button>`).join("");
}
$("#floors").onclick = e => { const f = e.target.dataset.f; if (f) viewFloor(f); };
function viewFloor(f, fit = true) {
  const changed = f !== S.view; S.view = f;
  if (changed || fit) { drawFloor(f); if (fit) fitFloor(); }
  drawMe(); drawRoute(false); drawFloors();
}
function fitFloor() {
  const F = S.floors[S.view], b = F.outline_rects.reduce((a, r) => [Math.min(a[0], r[0]), Math.min(a[1], r[1]), Math.max(a[2], r[2]), Math.max(a[3], r[3])], [1e9, 1e9, -1e9, -1e9]);
  const narrow = innerWidth < 700;
  map.fitBounds(rect(b), { paddingTopLeft: narrow ? [10, 150] : [400, 30], paddingBottomRight: narrow ? [10, 150] : [70, 100], animate: false });
}

/* ---------- state from server ---------- */
function applyState(st) {
  const floorChanged = st.floor !== S.me.floor;
  S.me = { floor: st.floor, x: st.x, y: st.y };
  S.nearby = Object.fromEntries(st.nearby.map(n => [n.room_id, n.dist]));
  S.can = { up: st.can_up, down: st.can_down };
  if (floorChanged) S.trail = [];
  S.trail.push([st.x, st.y]); if (S.trail.length > 400) S.trail.shift();
  S.hint = st.hint; S.here = st.here;
  const msg = $("#msg"); msg.hidden = !st.message; msg.textContent = st.message || "";
  if (floorChanged || !S.floors[S.view]) viewFloor(st.floor); else { markRoomClasses(); drawMe(); drawFloors(); }
  $("#status").innerHTML = `<b>${st.here ? st.here.name : "Corridor / lobby"}</b><span class="sub">Lt ${st.floor} · (${st.x}, ${st.y}) m</span>`;
  for (const [id, dir, sym] of [["up", "up", "↑"], ["down", "down", "↓"]]) {
    const b = $("#" + id); b.hidden = !S.can[dir]; b.textContent = st.hint ? `${sym} Change floor` : "";
    const m = st.hint.match(dir === "up" ? /E = up to Lt\. (\w+)/ : /Q = down to Lt\. (\w+)/);
    if (m) b.textContent = `${sym} Go to Lt ${m[1]}`;
  }
  if (S.dest) reroute();
}

async function act(path, extra = {}) {
  if (S.busy) return; S.busy = true;
  try { applyState(await api(path, { ...pos(), ...extra })); } finally { S.busy = false; }
}

/* ---------- controls ---------- */
document.querySelectorAll("[data-move]").forEach(b => b.onclick = () => { const [dx, dy] = b.dataset.move.split(",").map(Number); act("move", { dx, dy }); });
$("#up").onclick = () => act("change_floor", { up: true });
$("#down").onclick = () => act("change_floor", { up: false });
$("#goto").onsubmit = e => {
  e.preventDefault();
  const m = $("#gx").value.match(/-?\d+(\.\d+)?/g);
  if (m && m.length >= 2) act("goto", { tx: +m[0], ty: +m[1] });
};
$("#step").oninput = e => { S.step = +e.target.value; $("#stepv").textContent = S.step; };
$("#radius").oninput = e => { S.radius = +e.target.value; $("#radv").textContent = S.radius; act("nearby"); };
const KEYS = { w: [0, 1], a: [-1, 0], s: [0, -1], d: [1, 0], arrowup: [0, 1], arrowleft: [-1, 0], arrowdown: [0, -1], arrowright: [1, 0] };
document.addEventListener("keydown", e => {
  if (e.ctrlKey || e.metaKey || e.altKey || ["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
  const k = e.key.toLowerCase();
  if (KEYS[k]) { e.preventDefault(); act("move", { dx: KEYS[k][0], dy: KEYS[k][1] }); }
  else if (k === "e") act("change_floor", { up: true });
  else if (k === "q") act("change_floor", { up: false });
});

/* ---------- search ---------- */
let active = null;   // which input shows suggestions
function suggestions(q) {
  q = q.trim().toLowerCase();
  const score = r => { const hay = `${r.name} ${r.id} ${typeName(r.type)} lt ${r.floor}`.toLowerCase(); return q.split(/\s+/).every(t => hay.includes(t)) ? (r.name.toLowerCase().startsWith(q) ? 0 : 1) : 9; };
  return S.rooms.map(r => [score(r), r]).filter(x => x[0] < 9 && (q || LANDMARKS.includes(x[1].type))).sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name)).slice(0, 8).map(x => x[1]);
}
function showSuggest(input) {
  active = input; const list = suggestions(input.value), ul = $("#suggest");
  ul.innerHTML = list.map(r => `<li data-k="${r.key}">${r.name}<small>${typeName(r.type)} · Lt ${r.floor}</small></li>`).join("");
  ul.hidden = !list.length;
}
["from", "to"].forEach(id => {
  const el = $("#" + id);
  el.addEventListener("input", () => { showSuggest(el); $(`[data-clear=${id}]`).hidden = !el.value; });
  el.addEventListener("focus", () => showSuggest(el));
  el.addEventListener("keydown", e => { if (e.key === "Enter") { const li = $("#suggest li"); if (li) li.click(); } if (e.key === "Escape") $("#suggest").hidden = true; });
});
$("#suggest").onclick = e => {
  const li = e.target.closest("li"); if (!li) return;
  const r = S.roomByKey[li.dataset.k]; $("#suggest").hidden = true;
  if (active.id === "to") setDest(r); else setFrom(r);
};
document.addEventListener("click", e => { if (!e.target.closest("#search")) $("#suggest").hidden = true; });
document.querySelectorAll("[data-clear]").forEach(b => b.onclick = () => {
  if (b.dataset.clear === "to") clearDest(); else { $("#from").value = ""; b.hidden = true; }
});
function setFrom(r) { $("#from").value = r.name + " · Lt " + r.floor; $("[data-clear=from]").hidden = false; act("teleport", { key: r.key }); }
function setDest(r) {
  S.dest = r; $("#to").value = r.name + " · Lt " + r.floor; $("[data-clear=to]").hidden = false;
  markRoomClasses(); reroute(true);
}
function clearDest() {
  S.dest = null; S.route = null; $("#to").value = ""; $("[data-clear=to]").hidden = true;
  $("#directions").hidden = true; document.body.classList.remove("has-route");
  layers.route.clearLayers(); markRoomClasses(); drawFloors();
}

/* ---------- route + directions ---------- */
async function reroute(animate = false) {
  const my = ++S.seq;
  const r = await api("route", { ...pos(), to: S.dest.key });
  if (my !== S.seq || !S.dest) return;
  S.route = r; showDirections(r); drawFloors(); drawRoute(animate);
  if (animate && r.segments?.length) {
    const seg = r.segments.find(s => s.floor === S.view) || r.segments[0];
    if (seg.floor !== S.view) viewFloor(seg.floor, false);
  }
}
function drawRoute(animate) {
  layers.route.clearLayers();
  const r = S.route; if (!r) return;
  const segs = r.found ? r.segments.filter(s => s.floor === S.view) : (r.floor === S.view ? [{ points: r.fallback }] : []);
  segs.forEach((s, i) => {
    if (s.points.length < 2) return;
    const pts = s.points.map(p => ll(...p));
    L.polyline(pts, { className: "route-bg", interactive: false }).addTo(layers.route);
    const line = L.polyline(pts, { className: "route", interactive: false }).addTo(layers.route);
    if (animate) { const p = line.getElement(), len = p.getTotalLength(); p.style.strokeDasharray = len; p.style.strokeDashoffset = len; p.classList.add("draw"); }
  });
  const pin = (p, cls) => L.marker(ll(...p), { icon: L.divIcon({ className: "", html: `<div class="pin ${cls}"></div>`, iconSize: [0, 0] }), interactive: false, zIndexOffset: 500 }).addTo(layers.route);
  if (r.dest && String(r.dest.floor) === S.view) pin(r.dest.point, "");
  if (r.found && r.segments[0].floor === S.view && r.segments[0].points.length > 1) pin(r.segments[0].points[0], "start");
}
function showDirections(r) {
  const box = $("#directions"); box.hidden = false; document.body.classList.add("has-route");
  if (!r.found) { $("#summary").innerHTML = ""; $("#steps").innerHTML = `<li class="err">${r.error || "No route found."}</li>`; return; }
  const arrived = r.steps.length === 1;
  $("#summary").innerHTML = arrived ? "<b>You're here</b>" : `<b>${r.minutes} min</b> <span class="sub">· ${r.total_m} m walking · ${r.steps.filter(s => s.type === "floor").length} floor change${r.steps.filter(s => s.type === "floor").length > 1 ? "s" : ""}</span>`;
  const ico = { walk: "→", floor: "⇅", arrive: "⚑" };
  $("#steps").innerHTML = r.steps.map((s, i) =>
    `<li data-i="${i}"><span class="ico">${ico[s.type]}</span><span class="t">${s.text}${s.rooms.length ? `<br><span class="sub">Passing ${s.rooms.join(", ")}</span>` : ""}</span><span class="d">${s.dist ? s.dist + " m" : "Lt " + s.floor}</span></li>`).join("");
}
$("#steps").onclick = e => {
  const li = e.target.closest("li"); if (!li || !S.route?.steps) return;
  const s = S.route.steps[li.dataset.i]; viewFloor(s.floor, false); map.flyTo(ll(...s.point), Math.max(map.getZoom(), 3.5), { duration: .5 });
};
$("#sheet-handle").onclick = () => { const c = $("#directions").classList.toggle("collapsed"); document.body.classList.toggle("sheet-collapsed", c); };

/* ---------- legend, scale, theme ---------- */
$("#legend").innerHTML = Object.keys(CAT_NAME).map(k => `<span><i style="background:var(--c-${k})"></i>${CAT_NAME[k]}</span>`).join("");
function updateScale() {
  const k = Math.pow(2, map.getZoom()), nice = [1, 2, 5, 10, 20, 50, 100];
  const m = nice.filter(n => n * k <= 110).pop() || 1;
  const el = $("#scale"); el.style.width = m * k + "px"; el.textContent = m + " m";
}
map.on("zoom zoomend", updateScale);
function setTheme(t) { document.documentElement.dataset.theme = t; try { localStorage.setItem("theme", t); } catch (e) {} }
$("#theme").onclick = () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
let saved = null; try { saved = localStorage.getItem("theme"); } catch (e) {}
setTheme(saved || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));

/* ---------- boot ---------- */
(async function () {
  const [floors, rooms] = await Promise.all([api("map"), api("rooms")]);
  floors.forEach(f => { S.floors[f.floor] = f; S.order.push(f.floor); });
  S.rooms = rooms; rooms.forEach(r => S.roomByKey[r.key] = r);
  const f0 = S.order[0], st = S.floors[f0].start;
  S.me = { floor: f0, x: st[0], y: st[1] }; S.view = f0;
  viewFloor(f0);
  updateScale();
  await act("nearby");
  const to = new URLSearchParams(location.search).get("to");   // deep link: /?to=5:05001
  if (to && S.roomByKey[to]) setDest(S.roomByKey[to]);
})();
