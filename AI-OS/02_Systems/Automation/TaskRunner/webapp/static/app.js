// AI-OS web client. Vanilla JS, no framework or build step - this is a
// handful of screens fetching JSON, not an app that needs one. Every
// dashboard section here is a plain HTML render, not a markdown dump -
// that distinction is the whole reason this project exists.

const TOKEN_KEY = "aios_web_token";
const THREAD_KEY = "aios_thread_id";

function getToken() { return localStorage.getItem(TOKEN_KEY) || ""; }
function setToken(t) { localStorage.setItem(TOKEN_KEY, t.trim()); }

// Typing a 43-character random token on a phone keyboard into a masked
// field is genuinely error-prone (autocorrect, autocapitalize, no way to
// see what was actually typed before submitting) - this was the actual
// live bug, not a guess: the modal kept reappearing with no explanation,
// which reads exactly like "the token isn't accepted" whether it was
// wrong by one character or the save never even happened. A URL param
// removes typing entirely: opening
// http://<host>:<port>/?token=XXXX saves it automatically and cleans the
// URL afterward so it doesn't linger in history/bookmarks.
function bootstrapTokenFromUrl() {
  const params = new URLSearchParams(location.search);
  const fromUrl = params.get("token");
  if (fromUrl) {
    setToken(fromUrl);
    history.replaceState({}, "", location.pathname);
  }
}

// crypto.randomUUID() exists only in a secure context - HTTPS or localhost.
// This app is served over plain HTTP on the tailnet (Tailscale HTTPS certs
// are not enabled on Felix's account yet), so on his phone the function is
// simply undefined and every call threw "crypto.randomUUID is not a
// function" - which took the whole chat down, since getThreadId() runs
// before any message can be sent. crypto.getRandomValues IS available in an
// insecure context, so it does the work; Math.random is the last resort.
// This is an id for one person's own chat threads, not a security token.
function newId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const b = new Uint8Array(16);
    crypto.getRandomValues(b);
    b[6] = (b[6] & 0x0f) | 0x40;   // version 4
    b[8] = (b[8] & 0x3f) | 0x80;   // variant
    const hex = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function getThreadId() {
  let id = localStorage.getItem(THREAD_KEY);
  if (!id) {
    id = newId();
    localStorage.setItem(THREAD_KEY, id);
  }
  return id;
}
function newThreadId() {
  const id = newId();
  localStorage.setItem(THREAD_KEY, id);
  return id;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${getToken()}`,
      ...(options.headers || {}),
    },
  });
  if (res.status === 401) {
    showTokenModal();
    throw new Error("unauthorized");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function setConnDot(state) {
  const dot = document.getElementById("conn-dot");
  dot.className = "dot " + (state === "ok" ? "ok" : state === "err" ? "err" : "");
}

// --- token modal -----------------------------------------------------------

function showTokenModal() {
  document.getElementById("token-modal").classList.remove("hidden");
}
function hideTokenModal() {
  document.getElementById("token-modal").classList.add("hidden");
}

async function saveAndVerifyToken(val) {
  // Verified against a real endpoint before the modal closes - previously
  // this saved blindly and only found out it was wrong on the NEXT tab
  // switch, when the modal would silently reappear with no explanation.
  // That silence is what actually looked like "the token isn't accepted."
  const statusEl = document.getElementById("token-status");
  setToken(val);
  statusEl.textContent = "Prüfe...";
  statusEl.style.color = "";
  try {
    const res = await fetch("/api/money-board", {
      headers: { "Authorization": `Bearer ${getToken()}` },
    });
    if (res.status === 401) {
      statusEl.textContent = "Falscher Token - bitte nochmal genau abtippen oder den Link mit ?token=... öffnen.";
      statusEl.style.color = "var(--bad)";
      return false;
    }
    if (!res.ok) {
      statusEl.textContent = `Server-Fehler (${res.status}) - Token wurde trotzdem gespeichert.`;
      statusEl.style.color = "var(--bad)";
      return true; // token itself was accepted, something else is wrong
    }
    statusEl.textContent = "";
    return true;
  } catch (err) {
    statusEl.textContent = `Keine Verbindung zum Server (${err.message}). Bist du per Tailscale verbunden?`;
    statusEl.style.color = "var(--bad)";
    return false;
  }
}

document.getElementById("token-save").addEventListener("click", async () => {
  const val = document.getElementById("token-input").value.trim();
  if (!val) return;
  const ok = await saveAndVerifyToken(val);
  if (ok) {
    hideTokenModal();
    // Chat has no auto-loader (it waits for you to type), so switch to
    // Money first - otherwise a correct token on the Chat tab looks
    // exactly like a failed one, since nothing visibly happens either way.
    document.querySelector('.tab[data-screen="screen-money"]').click();
  }
});

// --- tabs --------------------------------------------------------------

const SCREEN_LOADERS = {
  "screen-money": loadMoneyBoard,
  "screen-dmarc": loadDmarcLeads,
  "screen-flips": loadFlipLog,
  "screen-downloads": loadFilesScreen,
  "screen-today": loadToday,
  "screen-snipes": loadSnipes,
  "screen-devices": loadDevices,
};

function loadActiveScreen() {
  const active = document.querySelector(".screen.active");
  const loader = SCREEN_LOADERS[active.id];
  if (loader) loader();
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (window.fxTap) window.fxTap();
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.screen).classList.add("active");
    // Lets CSS calm the atmosphere per screen - see [data-screen] in
    // style.css. Set here rather than read from .screen.active so the
    // stylesheet never has to know how the tab bar works.
    document.body.dataset.screen = btn.dataset.screen;
    // Live reads every time a tab opens, not cached - matches the backend's
    // own "no cache, always live" design (see api.py). A dashboard showing
    // stale numbers would defeat the point of having one.
    loadActiveScreen();
  });
});

// --- chat ----------------------------------------------------------------

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
let chatInFlight = false;

function addBubble(text, cls) {
  const div = document.createElement("div");
  div.className = `bubble ${cls}`;
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}

// Backs off from 1s to 4s: a fast answer still feels instant, a slow one
// stops hammering the server sixty times a minute for two minutes.
async function pollChatResult(taskId, bubble) {
  const started = Date.now();
  let wait = 1000;
  for (;;) {
    await new Promise((r) => setTimeout(r, wait));
    wait = Math.min(wait * 1.4, 4000);
    let res;
    try {
      res = await api("/api/chat-result", {
        method: "POST",
        body: JSON.stringify({ task_id: taskId }),
      });
    } catch (err) {
      // A failed poll is not a failed answer - the phone may have lost the
      // tailnet for a moment. Keep trying; the reply is on disk either way.
      const secs = Math.round((Date.now() - started) / 1000);
      bubble.textContent = `... (offline? ${secs}s)`;
      continue;
    }
    if (res.ready) return res.reply;
    if (res.lost) throw new Error(res.error || "Task verloren");
    const secs = res.elapsed ?? Math.round((Date.now() - started) / 1000);
    // Showing the count is the point: "still thinking, 40s" reads as slow,
    // a frozen "..." reads as broken.
    bubble.textContent = res.timed_out
      ? `... ${secs}s - dauert ungewöhnlich lange`
      : `... ${secs}s`;
  }
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (chatInFlight) return; // one message in flight, matching the backend's
                            // single-blocking-request design - no queueing
                            // a second message while the first is pending.
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  addBubble(text, "user");
  const pending = addBubble("...", "pending");
  chatInFlight = true;
  chatInput.disabled = true;
  try {
    // Enqueue, then poll. The send request now returns in milliseconds with a
    // ticket; the answer is collected separately. A real message on
    // 2026-09-01 took 93 seconds, the worker answered correctly, and Felix saw
    // "failed to fetch" - a phone browser will not hold a request open that
    // long through a screen blanking or a network switch. The reply existed
    // and was unreachable.
    const queued = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, thread_id: getThreadId() }),
    });
    setConnDot("ok");
    const reply = await pollChatResult(queued.task_id, pending);
    pending.textContent = reply;
    pending.className = "bubble assistant";
  } catch (err) {
    pending.textContent = `Fehler: ${err.message}`;
    pending.className = "bubble error";
    setConnDot("err");
  } finally {
    chatInFlight = false;
    chatInput.disabled = false;
    chatInput.focus();
  }
});

document.getElementById("new-conversation").addEventListener("click", () => {
  newThreadId();
  chatLog.innerHTML = "";
});

// --- today -----------------------------------------------------------------

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "Noch wach";
  if (h < 11) return "Morgen";
  if (h < 18) return "Nachmittag";
  return "Abend";
}

function switchTo(screenId) {
  document.querySelector(`.tab[data-screen="${screenId}"]`)?.click();
}

async function loadToday() {
  const greetEl = document.getElementById("today-greeting");
  const heroEl = document.getElementById("today-hero");
  const rowsEl = document.getElementById("today-rows");
  const quietEl = document.getElementById("today-quiet");
  greetEl.textContent = `${greeting()}, Felix`;
  try {
    const d = await api("/api/today");
    setConnDot("ok");
    const s = d.signals || {};

    // Exactly one bright thing on this screen. The reference artwork is a
    // single lit subject in a large dark field; three glowing cards would be
    // the opposite of it, and would also stop telling him what matters most.
    const a = d.next_action;
    heroEl.innerHTML = !a ? `<div class="hero"><div class="hero-label">Nichts offen</div>
        <div class="hero-action">Alles erledigt.</div></div>` : `
      <div class="hero">
        <div class="hero-label">${a.gates ? "Zuerst — blockiert den Rest" : "Als Nächstes"}</div>
        <div class="hero-action">${escapeHtml(a.action)}</div>
        <div class="hero-meta">
          ${a.euros ? `<span class="euros">~${a.euros} EUR</span>` : ""}
          <span>${a.minutes} min</span>
          <span>${d.open_actions} offen insgesamt</span>
        </div>
        <div class="hero-note">${escapeHtml(a.note || "")}</div>
      </div>`;

    // Quiet rows below: a number, a label, and where tapping goes. A zero is
    // rendered dim rather than hidden - "0 Briefe raus" is the single most
    // important fact on this screen and hiding it would be flattering.
    const rows = [
      { val: s.letters_sent ?? 0, lbl: "Briefe raus", to: "screen-dmarc",
        warn: (s.letters_sent ?? 0) === 0 },
      { val: s.leads_mailable ?? 0, lbl: "Leads mit Postadresse", to: "screen-dmarc" },
      { val: d.proposals_pending ?? 0, lbl: "Vorschläge warten auf dich", to: "screen-chat" },
      { val: d.study_pending ?? 0, lbl: "Study-Notizen unverarbeitet", to: "screen-downloads" },
      { val: s.flips?.open ?? 0, lbl: "Flips offen", to: "screen-flips" },
    ];
    rowsEl.innerHTML = rows.map((r) => `
      <div class="today-row" data-to="${r.to}">
        <span class="val ${r.val === 0 ? "zero" : ""} ${r.warn ? "warn" : ""}">${r.val}</span>
        <span class="lbl">${escapeHtml(r.lbl)}</span>
        <span class="chev">›</span>
      </div>`).join("");
    rowsEl.querySelectorAll(".today-row").forEach((el) => {
      el.addEventListener("click", () => {
        if (window.fxTap) window.fxTap();
        switchTo(el.dataset.to);
      });
    });

    // Hero first, then the rows behind it in sequence - the eye lands on the
    // one thing that matters before the supporting numbers arrive.
    if (window.fxReveal) {
      window.fxReveal(heroEl, ".hero", 0);
      window.fxReveal(rowsEl, ".today-row", 65);
    }
    if (window.fxCountUp) {
      rowsEl.querySelectorAll(".today-row .val").forEach((el) => {
        window.fxCountUp(el, el.textContent.trim());
      });
    }

    // Loaded separately and never awaited with the rest: the phone is often
    // unreachable (out of the house, rebooted since the last adb tcpip, or
    // simply off) and it must not be able to delay or break the screen that
    // has to be trustworthy at a glance.
    loadPhoneCard();

    const last = d.sniper?.last_run;
    quietEl.textContent = last
      ? `Sniper zuletzt ${new Date(last).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })} · ${d.sniper.alerted} Funde insgesamt`
      : "Sniper hat noch nicht gelaufen";
  } catch (err) {
    setConnDot("err");
    heroEl.innerHTML = `<div class="hero"><div class="hero-action">Fehler: ${escapeHtml(err.message)}</div></div>`;
  }
}

async function loadPhoneCard() {
  const el = document.getElementById("today-phone");
  if (!el) return;
  try {
    const p = await api("/api/phone");
    if (!p.reachable) {
      el.innerHTML = `<div class="phone-head"><span class="phone-dot off"></span>
        <span class="phone-label">Handy nicht erreichbar</span></div>`;
      return;
    }
    const b = p.battery || {};
    const notes = p.notifications || [];
    el.innerHTML = `
      <div class="phone-head">
        <span class="phone-dot ${b.charging ? "charging" : ""}"></span>
        <span class="phone-label">Handy</span>
        <span class="phone-meta">${b.level ?? "?"}%${b.charging ? " lädt" : ""} ·
          ${p.screen_on ? "Bildschirm an" : "Bildschirm aus"}</span>
      </div>
      ${notes.length ? notes.map((n) => `
        <div class="phone-note">
          <span class="np">${escapeHtml((n.package || "").split(".").pop())}</span>
          <span class="nt">${escapeHtml(n.title || "")}</span>
          <span class="nx">${escapeHtml(n.text || "")}</span>
        </div>`).join("")
        : `<div class="phone-note quiet">Nichts, was dich unterbrechen müsste.</div>`}
      ${p.filtered ? `<div class="phone-filtered">${p.filtered} Systemmeldung${p.filtered === 1 ? "" : "en"} ausgeblendet</div>` : ""}`;
  } catch (err) {
    el.innerHTML = `<div class="phone-head"><span class="phone-dot off"></span>
      <span class="phone-label">Handy: ${escapeHtml(err.message)}</span></div>`;
  }
}

// --- money board -----------------------------------------------------------

async function loadMoneyBoard() {
  const signalsEl = document.getElementById("money-signals");
  const cardsEl = document.getElementById("money-cards");
  try {
    const data = await api("/api/money-board");
    setConnDot("ok");
    const s = data.signals || {};
    const pills = [];
    if (s.letters_sent !== undefined) pills.push(`${s.letters_sent} Briefe raus`);
    if (s.leads_qualified !== undefined) pills.push(`${s.leads_qualified} Leads qualifiziert`);
    // Qualified and mailable are different numbers - only the overlap with an
    // OSM postal address can receive a letter. Showing the bigger one alone
    // overstates what a batch can actually reach.
    if (s.leads_mailable !== undefined) pills.push(`${s.leads_mailable} mit Postadresse`);
    if (s.flips && s.flips.open) pills.push(`${s.flips.open} Flips offen (${s.flips.capital_tied_up.toFixed(0)} EUR gebunden)`);
    signalsEl.innerHTML = pills.map((p) => `<span class="signal-pill">${escapeHtml(p)}</span>`).join("");

    if (!data.actions.length) {
      cardsEl.innerHTML = `<div class="empty-state">Nichts offen - alles erledigt.</div>`;
      return;
    }
    cardsEl.innerHTML = data.actions.map((a) => `
      <div class="card">
        <div class="card-top">
          <span class="card-euros${a.gates ? " card-gate" : ""}">${a.gates ? "ZUERST" : a.euros ? "~" + a.euros + " EUR" : "Basis"}</span>
          <span class="card-minutes">${a.minutes} min</span>
        </div>
        <div class="card-action">${escapeHtml(a.action)}</div>
        <div class="card-note">${escapeHtml(a.note)}</div>
      </div>
    `).join("");
  } catch (err) {
    setConnDot("err");
    cardsEl.innerHTML = `<div class="empty-state">Fehler beim Laden: ${escapeHtml(err.message)}</div>`;
  }
}

// --- dmarc leads -----------------------------------------------------------

function dmarcFinding(lead) {
  if (lead.dmarc === null || lead.dmarc === undefined) return "kein DMARC";
  if (lead.dmarc === "none") return "DMARC p=none";
  if (lead.dmarc === "quarantine") return "DMARC p=quarantine";
  return "DMARC aktiv";
}

async function loadDmarcLeads() {
  const summaryEl = document.getElementById("dmarc-summary");
  const tableEl = document.getElementById("dmarc-table");
  try {
    const data = await api("/api/dmarc-leads");
    setConnDot("ok");
    summaryEl.innerHTML = `<span class="signal-pill">${data.total_qualified} Leads insgesamt qualifiziert</span>
      <span class="signal-pill">zeigt Top ${data.leads.length}</span>`;
    if (!data.leads.length) {
      tableEl.innerHTML = `<div class="empty-state">Noch keine Leads.</div>`;
      return;
    }
    tableEl.innerHTML = data.leads.map((l) => `
      <div class="data-row">
        <div class="title">${escapeHtml(l.name || l.domain)}</div>
        <div class="subtitle">${escapeHtml(l.domain)}</div>
        <div class="meta">
          <span>Score ${l.score ?? "?"}</span>
          <span>${escapeHtml(dmarcFinding(l))}</span>
          ${l.provider ? `<span>${escapeHtml(l.provider)}</span>` : ""}
          ${l.address?.city ? `<span>${escapeHtml(l.address.city)}</span>` : ""}
          ${l.phone ? `<span>${escapeHtml(l.phone)}</span>` : ""}
        </div>
      </div>
    `).join("");
  } catch (err) {
    setConnDot("err");
    tableEl.innerHTML = `<div class="empty-state">Fehler beim Laden: ${escapeHtml(err.message)}</div>`;
  }
}

// --- device control --------------------------------------------------------

let deviceState = { id: null, list: [], width: 1080, height: 2400 };

function deviceSay(msg, bad) {
  const el = document.getElementById("device-status");
  el.textContent = msg || "";
  el.style.color = bad ? "var(--bad)" : "var(--text-faint)";
}

async function deviceAction(payload) {
  return api("/api/device-action", {
    method: "POST",
    body: JSON.stringify({ device: deviceState.id, ...payload }),
  });
}

async function loadDevices() {
  const tabsEl = document.getElementById("device-tabs");
  const infoEl = document.getElementById("device-info");
  try {
    const data = await api("/api/devices");
    setConnDot("ok");
    deviceState.list = data.devices || [];
    if (!deviceState.id || !deviceState.list.some((d) => d.id === deviceState.id)) {
      // Default to a device that is actually there, so the panel opens on
      // something usable instead of on whichever happens to be listed first.
      deviceState.id = (deviceState.list.find((d) => d.reachable)
        || deviceState.list[0] || {}).id;
    }
    tabsEl.innerHTML = deviceState.list.map((d) => `
      <button class="chip ${d.id === deviceState.id ? "on" : ""}" data-dev="${d.id}">
        ${escapeHtml(d.label)}${d.reachable ? "" : " · offline"}
      </button>`).join("");
    tabsEl.querySelectorAll(".chip").forEach((el) => el.addEventListener("click", () => {
      if (window.fxTap) window.fxTap();
      deviceState.id = el.dataset.dev;
      loadDevices();
    }));

    const dev = deviceState.list.find((d) => d.id === deviceState.id) || {};
    if (!dev.reachable) {
      infoEl.innerHTML = `<div class="empty-state">${escapeHtml(dev.reason || "nicht erreichbar")}</div>`;
      document.getElementById("device-screen-wrap").innerHTML = "";
      document.getElementById("device-controls").innerHTML = "";
      return;
    }
    deviceState.width = dev.width || 1080;
    deviceState.height = dev.height || 2400;
    const b = dev.battery || {};
    infoEl.innerHTML = `<span>${b.level ?? "?"}%${b.charging ? " lädt" : ""}</span>
      <span>${dev.screen_on ? "Bildschirm an" : "Bildschirm aus"}</span>
      <span>${escapeHtml(dev.current_app || "—")}</span>
      <span>${dev.rooted ? "root" : "ohne root"}</span>`;
    renderDeviceControls();
    loadNodeRunner();
    await refreshDeviceScreen();
  } catch (err) {
    setConnDot("err");
    infoEl.innerHTML = `<div class="empty-state">Fehler: ${escapeHtml(err.message)}</div>`;
  }
}

function renderDeviceControls() {
  const el = document.getElementById("device-controls");
  el.innerHTML = `
    <div class="chip-row">
      <button class="chip" data-key="back">Zurück</button>
      <button class="chip" data-key="home">Home</button>
      <button class="chip" data-key="recents">Apps</button>
      <button class="chip" data-key="wake">Wecken</button>
      <button class="chip" data-key="sleep">Sperren</button>
      <button class="chip" id="dev-refresh">Neu laden</button>
    </div>
    <div class="device-typerow">
      <input id="dev-text" type="text" placeholder="Text aufs Handy tippen..." autocomplete="off">
      <button class="upload-send" id="dev-send">Senden</button>
    </div>`;
  el.querySelectorAll("[data-key]").forEach((b) => b.addEventListener("click", async () => {
    if (window.fxTap) window.fxTap();
    deviceSay(`${b.textContent}...`);
    const r = await deviceAction({ action: "key", key: b.dataset.key });
    deviceSay(r.ok ? "" : r.error, !r.ok);
    // The screen almost always changed after a key, so re-grab it rather
    // than leaving a stale picture that looks like nothing happened.
    await refreshDeviceScreen();
  }));
  el.querySelector("#dev-refresh").addEventListener("click", refreshDeviceScreen);
  const send = async () => {
    const input = document.getElementById("dev-text");
    if (!input.value.trim()) return;
    deviceSay("tippe...");
    const r = await deviceAction({ action: "text", text: input.value });
    input.value = "";
    deviceSay(r.ok ? "" : r.error, !r.ok);
    await refreshDeviceScreen();
  };
  el.querySelector("#dev-send").addEventListener("click", send);
  el.querySelector("#dev-text").addEventListener("keydown", (e) => {
    if (e.key === "Enter") send();
  });
}

async function refreshDeviceScreen() {
  const wrap = document.getElementById("device-screen-wrap");
  deviceSay("Bildschirm holen...");
  try {
    const r = await deviceAction({ action: "screenshot" });
    if (!r.ok) { deviceSay(r.error, true); return; }
    deviceState.width = r.width || deviceState.width;
    deviceState.height = r.height || deviceState.height;
    // Fetched as a blob with the auth header, not set as a plain src: an
    // <img> request carries no Authorization header, so the gated endpoint
    // answers 401 and the browser shows a broken image. Same reason
    // downloadFile() does it this way - caught here by screenshotting the
    // panel rather than by reading the code.
    const res = await fetch(r.url, { headers: { Authorization: `Bearer ${getToken()}` } });
    if (!res.ok) { deviceSay(`Bild ${res.status}`, true); return; }
    const blob = await res.blob();
    // Revoke the previous one: a screenshot every few seconds would otherwise
    // leak a megabyte at a time for as long as the panel stays open.
    if (deviceState.blobUrl) URL.revokeObjectURL(deviceState.blobUrl);
    deviceState.blobUrl = URL.createObjectURL(blob);
    wrap.innerHTML = `<img id="dev-img" class="device-screen" src="${deviceState.blobUrl}" alt="Bildschirm">`;
    deviceSay("");
    const img = document.getElementById("dev-img");
    img.addEventListener("click", async (e) => {
      // Map the click back to device pixels. The image is displayed at
      // whatever width the phone browser gives it, so a tap 40% across has
      // to become 40% of 1080 - not 40% of the CSS width.
      const rect = img.getBoundingClientRect();
      const x = Math.round(((e.clientX - rect.left) / rect.width) * deviceState.width);
      const y = Math.round(((e.clientY - rect.top) / rect.height) * deviceState.height);
      if (window.fxTap) window.fxTap();
      deviceSay(`tippe ${x},${y}...`);
      const t = await deviceAction({ action: "tap", x, y });
      deviceSay(t.ok ? "" : t.error, !t.ok);
      await refreshDeviceScreen();
    });
  } catch (err) {
    deviceSay(err.message, true);
  }
}

// --- remote command on a compute node ---------------------------------------

let nodeState = { id: null };

async function loadNodeRunner() {
  const listEl = document.getElementById("node-list");
  if (!listEl) return;
  try {
    const data = await api("/api/nodes");
    const nodes = data.nodes || [];
    if (!nodeState.id || !nodes.some((n) => n.id === nodeState.id && n.online)) {
      nodeState.id = (nodes.find((n) => n.online) || {}).id || null;
    }
    listEl.innerHTML = nodes.map((n) => `
      <button class="chip ${n.id === nodeState.id ? "on" : ""}" data-node="${escapeHtml(n.id)}"
              ${n.online ? "" : "disabled"}>
        ${escapeHtml(n.id)} · ${n.cores ?? "?"}K${n.online ? "" : " offline"}
      </button>`).join("") || `<span class="hint">Keine Knoten.</span>`;
    listEl.querySelectorAll(".chip").forEach((el) => el.addEventListener("click", () => {
      if (el.disabled) return;
      if (window.fxTap) window.fxTap();
      nodeState.id = el.dataset.node;
      loadNodeRunner();
    }));
  } catch (err) {
    listEl.innerHTML = `<span class="hint">Fehler: ${escapeHtml(err.message)}</span>`;
  }
}

async function runOnNode() {
  const input = document.getElementById("node-cmd");
  const out = document.getElementById("node-output");
  const cmd = input.value.trim();
  if (!cmd) return;
  if (!nodeState.id) { out.textContent = "Kein Knoten ausgewählt."; return; }
  out.textContent = `[${nodeState.id}] wird eingereiht...`;
  try {
    const queued = await api("/api/node-run", {
      method: "POST",
      body: JSON.stringify({ node: nodeState.id, command: cmd }),
    });
    input.value = "";
    // Polled, not awaited in one request: the command may sit in the queue
    // while the laptop is asleep, and a browser will not hold a request open
    // that long - the same failure the chat had.
    let wait = 800;
    for (;;) {
      await new Promise((r) => setTimeout(r, wait));
      wait = Math.min(wait * 1.3, 4000);
      const res = await api("/api/node-result", {
        method: "POST",
        body: JSON.stringify({ job_id: queued.job_id }),
      });
      if (res.ready) {
        out.textContent = (res.ok ? "" : "[fehlgeschlagen] ")
          + (res.output || "(keine Ausgabe)");
        return;
      }
      if (res.lost) { out.textContent = res.error; return; }
      out.textContent = `[${nodeState.id}] ${res.state}...`;
    }
  } catch (err) {
    out.textContent = `Fehler: ${err.message}`;
  }
}

// --- snipes ----------------------------------------------------------------

// Filter state lives here rather than in the DOM so a re-render (which
// replaces the whole list) cannot lose it.
const snipeFilters = { tier: null, watch: null, max_price: null, max_distance: null };

const TIER_ORDER = ["S", "A", "B", "C", "D"];

async function loadSnipes() {
  const filtersEl = document.getElementById("snipe-filters");
  const listEl = document.getElementById("snipe-list");
  try {
    const data = await api("/api/snipes", {
      method: "POST",
      body: JSON.stringify(snipeFilters),
    });
    setConnDot("ok");

    // Tier chips show UNFILTERED totals - what exists, not what survived the
    // current filter. A chip that reads "S 0" because S is filtered out would
    // be telling you the opposite of the truth.
    const counts = data.tier_counts || {};
    const chips = TIER_ORDER
      .filter((t) => counts[t])
      .map((t) => `<button class="chip tier-${t} ${snipeFilters.tier === t ? "on" : ""}" data-tier="${t}">${t} · ${counts[t]}</button>`)
      .join("");
    const watchChips = (data.watches || [])
      .map((w) => `<button class="chip ${snipeFilters.watch === w ? "on" : ""}" data-watch="${escapeHtml(w)}">${escapeHtml(w)}</button>`)
      .join("");
    filtersEl.innerHTML = `
      <div class="chip-row">${chips}</div>
      <div class="chip-row">${watchChips}</div>
      <div class="chip-row">
        <button class="chip ${snipeFilters.max_distance === 15 ? "on" : ""}" data-dist="15">≤15 km</button>
        <button class="chip ${snipeFilters.max_price === 30 ? "on" : ""}" data-price="30">≤30 €</button>
        <button class="chip clear">Filter zurücksetzen</button>
      </div>`;

    // Toggle semantics: tapping an active filter clears it. On a phone that
    // is the only way to undo a filter without hunting for a reset button.
    filtersEl.querySelectorAll(".chip").forEach((el) => {
      el.addEventListener("click", () => {
        if (window.fxTap) window.fxTap();
        if (el.classList.contains("clear")) {
          Object.keys(snipeFilters).forEach((k) => { snipeFilters[k] = null; });
        } else if (el.dataset.tier) {
          snipeFilters.tier = snipeFilters.tier === el.dataset.tier ? null : el.dataset.tier;
        } else if (el.dataset.watch) {
          snipeFilters.watch = snipeFilters.watch === el.dataset.watch ? null : el.dataset.watch;
        } else if (el.dataset.dist) {
          snipeFilters.max_distance = snipeFilters.max_distance ? null : Number(el.dataset.dist);
        } else if (el.dataset.price) {
          snipeFilters.max_price = snipeFilters.max_price ? null : Number(el.dataset.price);
        }
        loadSnipes();
      });
    });

    if (!data.snipes.length) {
      listEl.innerHTML = `<div class="empty-state">${data.total ? "Nichts passt zu diesen Filtern." : "Noch keine Funde."}</div>`;
      return;
    }

    listEl.innerHTML = data.snipes.map((s) => {
      const price = s.price === 0 ? "zu verschenken"
        : (s.price === null || s.price === undefined ? "kein Preis" : s.price + " €");
      const dist = s.distance === null || s.distance === undefined ? "im Ort" : s.distance + " km";
      return `
        <a class="data-row snipe" href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer">
          <div class="snipe-head">
            <span class="tier-badge tier-${s.tier}">${s.tier}</span>
            <span class="title">${escapeHtml(s.title)}</span>
          </div>
          <div class="meta">
            <span class="${s.price === 0 ? "free" : ""}">${escapeHtml(price)}</span>
            <span>${escapeHtml(dist)}</span>
            <span>${escapeHtml(s.watch || "")}</span>
          </div>
          <div class="reasons">${escapeHtml((s.reasons || []).join(" · "))}</div>
        </a>`;
    }).join("");
    if (window.fxReveal) window.fxReveal(listEl, ".data-row", 35);
  } catch (err) {
    setConnDot("err");
    listEl.innerHTML = `<div class="empty-state">Fehler: ${escapeHtml(err.message)}</div>`;
  }
}

// --- flip log --------------------------------------------------------------

async function loadFlipLog() {
  const tableEl = document.getElementById("flips-table");
  try {
    const data = await api("/api/flip-log");
    setConnDot("ok");
    if (!data.rows.length) {
      tableEl.innerHTML = `<div class="empty-state">Noch keine Flips geloggt.</div>`;
      return;
    }
    tableEl.innerHTML = data.rows.map((r) => {
      const net = parseFloat((r["Net €"] || "").replace(",", "."));
      // CSS keys off "net win" / "net loss" together (.net.win, .net.loss) so
      // the neutral ".net" rule and the colour rule can both apply; a plain
      // "win"/"loss" class here left the amount in default grey with no error
      // anywhere, since escapeHtml() happily wrote the wrong class name too.
      const netCls = r.open ? "open" : `net ${net < 0 ? "loss" : "win"}`;
      return `
        <div class="data-row">
          <div class="title">${escapeHtml(r.Item || "")}</div>
          <div class="subtitle">${escapeHtml(r.Date || "")} · ${escapeHtml(r.Category || "")}</div>
          <div class="meta">
            <span>Kauf ${escapeHtml(r["Buy €"] || "?")} €</span>
            <span class="${netCls}">${r.open ? "offen" : `Netto ${escapeHtml(r["Net €"] || "")} €`}</span>
            ${!r.open && r["€/hour"] ? `<span>${escapeHtml(r["€/hour"])} €/h</span>` : ""}
          </div>
        </div>`;
    }).join("");
  } catch (err) {
    setConnDot("err");
    tableEl.innerHTML = `<div class="empty-state">Fehler beim Laden: ${escapeHtml(err.message)}</div>`;
  }
}

// --- downloads ---------------------------------------------------------

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

async function downloadFile(url, name, btn) {
  // Fetched as a blob with the auth header, not linked to directly - the
  // token never appears in a URL or browser history this way, and
  // server.py gates /downloads/* on exactly this header (see server.py).
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "...";
  try {
    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(blobUrl);
  } catch (err) {
    alert(`Download fehlgeschlagen: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

// --- uploads ---------------------------------------------------------------

// Files go up as raw bytes with the name in the query string, one request
// each - NOT multipart/form-data. Nothing but this client will ever call
// the endpoint, so there is no interop reason for the server to hand-roll a
// multipart parser (Python removed the stdlib one in 3.13).
async function uploadOne(file) {
  const res = await fetch(`/api/upload?name=${encodeURIComponent(file.name)}`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${getToken()}`,
      "Content-Type": "application/octet-stream",
    },
    body: file,
  });
  if (res.status === 401) {
    showTokenModal();
    throw new Error("unauthorized");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function sendSelectedUploads() {
  const input = document.getElementById("upload-input");
  const statusEl = document.getElementById("upload-status");
  const btn = document.getElementById("upload-send");
  const files = Array.from(input.files || []);
  if (!files.length) return;
  btn.disabled = true;
  let done = 0;
  const failed = [];
  for (const file of files) {
    // Counted one by one rather than after the whole batch: a phone on a
    // slow tailnet takes real seconds per file, and a button that just sits
    // there reads as broken rather than busy.
    statusEl.textContent = `Lade hoch (${done + 1}/${files.length}): ${file.name}`;
    statusEl.style.color = "";
    try {
      await uploadOne(file);
      done += 1;
    } catch (err) {
      failed.push(`${file.name}: ${err.message}`);
    }
  }
  input.value = "";
  updateUploadButton();
  statusEl.textContent = failed.length
    ? `${done} hochgeladen, ${failed.length} fehlgeschlagen - ${failed.join("; ")}`
    : `${done} Datei(en) hochgeladen.`;
  statusEl.style.color = failed.length ? "var(--bad)" : "var(--good)";
  loadUploads();
}

function updateUploadButton() {
  const input = document.getElementById("upload-input");
  document.getElementById("upload-send").disabled = !(input.files || []).length;
}

// Both uploads and downloads are already sorted newest-first by the
// server, so capping here always keeps the most recent items visible - the
// ones actually worth seeing without hunting. Purely client-side: the full
// list already arrived in one request, so "show more" just reveals more of
// what is already in memory, no extra round trip. Felix asked for this
// directly: a semester of photographed slides or a summer of DMARC PDFs
// would otherwise mean scrolling through hundreds of rows to find anything.
const LIST_PAGE_SIZE = 20;

function renderCapped(listEl, items, toHtml, opts = {}) {
  const pageSize = opts.pageSize || LIST_PAGE_SIZE;
  let shown = pageSize;
  const render = () => {
    const visible = items.slice(0, shown);
    const remaining = items.length - visible.length;
    listEl.innerHTML = visible.map(toHtml).join("") + (remaining > 0
      ? `<button class="show-more-btn" id="list-show-more">Mehr anzeigen (${remaining} weitere)</button>`
      : "");
    if (opts.afterRender) opts.afterRender(listEl);
    // Only the newly revealed slice animates in. Re-staggering the whole
    // list on every "show more" would replay the entrance for rows the user
    // has already been looking at.
    if (window.fxReveal) {
      const fresh = Array.from(listEl.querySelectorAll(".card")).slice(shown - pageSize);
      fresh.forEach((el, i) => {
        el.classList.add("fx-in");
        el.style.animationDelay = `${i * 45}ms`;
      });
    }
    const moreBtn = document.getElementById("list-show-more");
    if (moreBtn) moreBtn.addEventListener("click", () => {
      shown += pageSize;
      render();
    });
  };
  render();
}

async function loadUploads() {
  const listEl = document.getElementById("uploads-list");
  try {
    const data = await api("/api/uploads");
    if (!data.files.length) {
      listEl.innerHTML = `<div class="empty-state">Noch nichts hochgeladen.</div>`;
      return;
    }
    // No download link, unlike the generated files below: these are his own
    // private chat exports, already on his phone. Re-serving them would add
    // exposure for nothing.
    renderCapped(listEl, data.files, (f) => `
      <div class="card">
        <div class="card-action">${escapeHtml(f.name)}</div>
        <div class="download-meta">${formatBytes(f.size)} · ${escapeHtml(f.modified.replace("T", " "))}</div>
      </div>
    `);
  } catch (err) {
    listEl.innerHTML = `<div class="empty-state">Fehler: ${escapeHtml(err.message)}</div>`;
  }
}

async function buildVoiceProfile() {
  const btn = document.getElementById("voice-build");
  const statusEl = document.getElementById("voice-status");
  btn.disabled = true;
  statusEl.style.color = "";
  statusEl.textContent = "Baue Profil...";
  try {
    const data = await api("/api/voice-import", { method: "POST", body: "{}" });
    statusEl.textContent = data.output || `Profil aus ${data.files} Chats gebaut.`;
    statusEl.style.color = "var(--good)";
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.style.color = "var(--bad)";
  } finally {
    btn.disabled = false;
  }
}

async function loadFilesScreen() {
  await Promise.all([loadUploads(), loadDownloads()]);
}

async function loadDownloads() {
  const listEl = document.getElementById("downloads-list");
  try {
    const data = await api("/api/downloads");
    setConnDot("ok");
    if (!data.files.length) {
      listEl.innerHTML = `<div class="empty-state">Noch keine Dateien. Bitte den Bot im Chat, dir etwas zu erstellen.</div>`;
      return;
    }
    renderCapped(listEl, data.files, (f) => `
      <div class="card">
        <div class="download-row">
          <div>
            <div class="card-action">${escapeHtml(f.name)}</div>
            <div class="download-meta">${formatBytes(f.size)} · ${escapeHtml(f.modified.replace("T", " "))}</div>
          </div>
          <button class="download-btn" data-url="${escapeHtml(f.url)}" data-name="${escapeHtml(f.name)}">
            Herunterladen
          </button>
        </div>
      </div>
    `, {
      // Re-wired after every render, including "show more" clicks, since
      // renderCapped replaces innerHTML each time - listeners on the
      // previous DOM nodes are gone with them.
      afterRender: (el) => el.querySelectorAll(".download-btn").forEach((btn) => {
        btn.addEventListener("click", () =>
          downloadFile(btn.dataset.url, btn.dataset.name, btn));
      }),
    });
  } catch (err) {
    setConnDot("err");
    listEl.innerHTML = `<div class="empty-state">Fehler beim Laden: ${escapeHtml(err.message)}</div>`;
  }
}

// --- utils -----------------------------------------------------------------

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

// --- upload wiring ---------------------------------------------------------

document.getElementById("upload-input").addEventListener("change", updateUploadButton);
document.getElementById("upload-send").addEventListener("click", sendSelectedUploads);
document.getElementById("voice-build").addEventListener("click", buildVoiceProfile);

// --- install prompt --------------------------------------------------------

// Chrome fires beforeinstallprompt only when the app is genuinely
// installable - served over HTTPS, with a manifest and a registered service
// worker. Over plain HTTP none of that holds, so this button simply never
// appears, which is the honest signal: if you cannot see it, the app is not
// installable yet and the reason is the missing certificate, not the button.
let deferredInstall = null;

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstall = e;
  document.getElementById("install-btn").classList.remove("hidden");
});

document.getElementById("install-btn").addEventListener("click", async () => {
  if (!deferredInstall) return;
  deferredInstall.prompt();
  await deferredInstall.userChoice;
  deferredInstall = null;
  document.getElementById("install-btn").classList.add("hidden");
});

window.addEventListener("appinstalled", () => {
  document.getElementById("install-btn").classList.add("hidden");
});

document.getElementById("node-send")?.addEventListener("click", runOnNode);
document.getElementById("node-cmd")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runOnNode();
});

// --- boot ------------------------------------------------------------------

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

bootstrapTokenFromUrl();

document.body.dataset.screen =
  document.querySelector(".screen.active")?.id || "screen-today";

if (!getToken()) {
  showTokenModal();
} else {
  loadActiveScreen();
}
