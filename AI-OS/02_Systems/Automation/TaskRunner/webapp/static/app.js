// AI-OS web client. Vanilla JS, no framework or build step - this is a
// handful of screens fetching JSON, not an app that needs one. Every
// dashboard section here is a plain HTML render, not a markdown dump -
// that distinction is the whole reason this project exists.

const TOKEN_KEY = "aios_web_token";
const THREAD_KEY = "aios_thread_id";
const SESSION_KEY = "aios_claude_session";

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

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function ago(seconds) {
  if (seconds < 60) return "gerade eben";
  if (seconds < 3600) return `vor ${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `vor ${Math.round(seconds / 3600)} h`;
  return `vor ${Math.round(seconds / 86400)} d`;
}

function usd(n) {
  const v = Number(n || 0);
  return (v < 1 && v > 0 ? v.toFixed(3) : v.toFixed(2));
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
  statusEl.textContent = "Prüfe…";
  statusEl.style.color = "";
  try {
    const res = await fetch("/api/money-board", {
      headers: { "Authorization": `Bearer ${getToken()}` },
    });
    if (res.status === 401) {
      statusEl.textContent = "Falscher Token — bitte nochmal genau abtippen oder den Link mit ?token=… öffnen.";
      statusEl.style.color = "var(--bad)";
      return false;
    }
    if (!res.ok) {
      statusEl.textContent = `Server-Fehler (${res.status}) — Token wurde trotzdem gespeichert.`;
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
  if (await saveAndVerifyToken(val)) {
    hideTokenModal();
    switchTo("screen-today");
  }
});

// --- navigation ------------------------------------------------------------

const SCREEN_LOADERS = {
  "screen-today": loadToday,
  "screen-chat": loadChat,
  "screen-devices": loadDevices,
  "screen-money": loadMoneyBoard,
  "screen-costs": loadCosts,
  "screen-dmarc": loadDmarcLeads,
  "screen-snipes": loadSnipes,
  "screen-flips": loadFlipLog,
  "screen-downloads": loadFilesScreen,
};

// Screens that are NOT in the tab bar. Nine screens do not fit across a
// phone - the previous version put all of them there and the last one was
// literally cut in half by the edge of the display. Five stay, the rest
// live behind "Mehr", which is also where a screen goes when it is a place
// you visit rather than a place you live.
const MORE_SCREENS = [
  { id: "screen-costs", label: "Kosten", icon: "M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" },
  { id: "screen-dmarc", label: "DMARC-Leads", icon: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" },
  { id: "screen-snipes", label: "Snipes", icon: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16M12 2v3M12 19v3M2 12h3M19 12h3" },
  { id: "screen-flips", label: "Flip-Log", icon: "M3 8h14l-3-3M21 16H7l3 3" },
  { id: "screen-downloads", label: "Dateien", icon: "M4 4h6l2 3h8v13H4z" },
];

let currentScreen = "screen-today";

function switchTo(screenId) {
  if (window.fxTap) window.fxTap();
  // The live phone picture is a running ffmpeg on the server and a held-open
  // connection. Leaving the screen must end it, or walking away from the
  // device tab quietly keeps recording a phone nobody is looking at.
  if (currentScreen === "screen-devices" && screenId !== "screen-devices") stopStream();
  currentScreen = screenId;
  document.querySelectorAll(".screen").forEach((s) => s.classList.toggle("active", s.id === screenId));
  document.querySelectorAll(".tab").forEach((b) =>
    b.classList.toggle("active", b.dataset.screen === screenId));
  // Nothing in the bar corresponds to a screen that lives behind "Mehr", so
  // that button carries the highlight instead - a tab bar with no selection
  // reads as a broken one.
  document.getElementById("more-tab").classList.toggle(
    "active", MORE_SCREENS.some((s) => s.id === screenId));
  // Lets CSS calm the atmosphere per screen - see #fx-veil in style.css.
  document.body.dataset.screen = screenId;
  closeSheet();
  // Live reads every time a screen opens, not cached - matches the backend's
  // own "no cache, always live" design (see api.py). A dashboard showing
  // stale numbers would defeat the point of having one.
  const loader = SCREEN_LOADERS[screenId];
  if (loader) loader();
}

function loadActiveScreen() { switchTo(currentScreen); }

document.querySelectorAll(".tab[data-screen]").forEach((btn) => {
  btn.addEventListener("click", () => switchTo(btn.dataset.screen));
});

// --- sheet -----------------------------------------------------------------

function openSheet(html, wire) {
  const wrap = document.getElementById("sheet");
  document.getElementById("sheet-body").innerHTML = html;
  wrap.classList.remove("hidden");
  if (wire) wire(document.getElementById("sheet-body"));
}
function closeSheet() {
  document.getElementById("sheet").classList.add("hidden");
}
document.querySelector("#sheet .sheet-scrim").addEventListener("click", closeSheet);

document.getElementById("more-tab").addEventListener("click", () => {
  if (window.fxTap) window.fxTap();
  openSheet(MORE_SCREENS.map((s) => `
    <button class="sheet-item ${s.id === currentScreen ? "on" : ""}" data-to="${s.id}">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor"
           stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="${s.icon}"/></svg>
      ${escapeHtml(s.label)}
    </button>`).join(""),
    (root) => root.querySelectorAll(".sheet-item").forEach((el) =>
      el.addEventListener("click", () => switchTo(el.dataset.to))));
});

// --- today -----------------------------------------------------------------

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "Noch wach";
  if (h < 11) return "Morgen";
  if (h < 18) return "Nachmittag";
  return "Abend";
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
    heroEl.innerHTML = !a
      ? `<div class="hero"><div class="kicker">Nichts offen</div>
           <div class="title">Alles erledigt.</div></div>`
      : `<div class="hero">
          <div class="kicker">${a.gates ? "Zuerst — blockiert den Rest" : "Als Nächstes"}</div>
          <div class="title">${escapeHtml(a.action)}</div>
          <div class="meta">
            ${a.euros ? `<span>~${a.euros} EUR</span>` : ""}
            <span>${a.minutes} min</span>
            <span>${d.open_actions} offen</span>
          </div>
          ${a.note ? `<div class="body">${escapeHtml(a.note)}</div>` : ""}
        </div>`;

    // Quiet rows below: a number, a label, and where tapping goes. A zero is
    // rendered dim rather than hidden - "0 Briefe raus" is the single most
    // important fact on this screen and hiding it would be flattering.
    const rows = [
      { val: s.letters_sent ?? 0, lbl: "Briefe raus", to: "screen-dmarc" },
      { val: s.leads_mailable ?? 0, lbl: "Leads mit Postadresse", to: "screen-dmarc", hot: true },
      { val: d.proposals_pending ?? 0, lbl: "Vorschläge warten auf dich", to: "screen-chat" },
      { val: d.study_pending ?? 0, lbl: "Study-Notizen unverarbeitet", to: "screen-downloads" },
      { val: s.flips?.open ?? 0, lbl: "Flips offen", to: "screen-flips" },
    ];
    rowsEl.innerHTML = rows.map((r) => `
      <div class="stat-row" data-to="${r.to}">
        <span class="num ${r.val === 0 ? "zero" : (r.hot ? "hot" : "")}">${r.val}</span>
        <span class="label">${escapeHtml(r.lbl)}</span>
      </div>`).join("");
    rowsEl.querySelectorAll(".stat-row").forEach((el) =>
      el.addEventListener("click", () => switchTo(el.dataset.to)));

    // Hero first, then the rows behind it in sequence - the eye lands on the
    // one thing that matters before the supporting numbers arrive.
    if (window.fxReveal) {
      window.fxReveal(heroEl, ".hero", 0);
      window.fxReveal(rowsEl, ".stat-row", 60);
    }
    if (window.fxCountUp) {
      rowsEl.querySelectorAll(".stat-row .num").forEach((el) =>
        window.fxCountUp(el, el.textContent.trim()));
    }
    litPanels(heroEl);

    // Loaded separately and never awaited with the rest: the phone is often
    // unreachable (out of the house, rebooted since the last adb tcpip, or
    // simply off) and it must not be able to delay or break the screen that
    // has to be trustworthy at a glance.
    loadPhoneCard();
    refreshCostPill();

    const last = d.sniper?.last_run;
    quietEl.textContent = last
      ? `Sniper zuletzt ${new Date(last).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })} · ${d.sniper.alerted} Funde insgesamt`
      : "Sniper hat noch nicht gelaufen";
  } catch (err) {
    setConnDot("err");
    heroEl.innerHTML = `<div class="hero"><div class="title">Fehler: ${escapeHtml(err.message)}</div></div>`;
  }
}

async function loadPhoneCard() {
  const el = document.getElementById("today-phone");
  if (!el) return;
  try {
    const p = await api("/api/phone");
    if (!p.reachable) {
      el.innerHTML = `<div class="card"><div class="sub">Handy nicht erreichbar</div></div>`;
      return;
    }
    const b = p.battery || {};
    const notes = p.notifications || [];
    el.innerHTML = `
      <div class="card" style="margin-top:18px">
        <div class="row">
          <h3>Handy</h3>
          <span class="sub">${b.level ?? "?"}%${b.charging ? " lädt" : ""} ·
            ${p.screen_on ? "Bildschirm an" : "aus"}</span>
        </div>
        ${notes.length ? notes.map((n) => `
          <div class="list-line">
            <span><span class="who">${escapeHtml((n.package || "").split(".").pop())}</span>
              ${escapeHtml(n.title || "")}</span>
            <span class="when">${escapeHtml((n.text || "").slice(0, 40))}</span>
          </div>`).join("")
          : `<div class="sub" style="margin-top:8px">Nichts, was dich unterbrechen müsste.</div>`}
        ${p.filtered ? `<div class="sub" style="margin-top:8px;opacity:.6">${p.filtered} Systemmeldung${p.filtered === 1 ? "" : "en"} ausgeblendet</div>` : ""}
      </div>`;
    litPanels(el);
  } catch (err) {
    el.innerHTML = `<div class="card"><div class="sub">Handy: ${escapeHtml(err.message)}</div></div>`;
  }
}

// --- the specular highlight ------------------------------------------------

// Cards catch light under the finger. Bound per render because every screen
// replaces its own innerHTML; the listener is on the card itself so a scroll
// gesture that never touches one costs nothing.
function litPanels(root) {
  (root || document).querySelectorAll(".card, .hero, .panel, .balance").forEach((el) => {
    if (el.dataset.lit) return;
    el.dataset.lit = "1";
    const move = (e) => {
      const t = e.touches ? e.touches[0] : e;
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${((t.clientX - r.left) / r.width) * 100}%`);
      el.style.setProperty("--my", `${((t.clientY - r.top) / r.height) * 100}%`);
      el.classList.add("lit");
    };
    el.addEventListener("pointerdown", move);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", () => el.classList.remove("lit"));
    el.addEventListener("pointerup", () => setTimeout(() => el.classList.remove("lit"), 500));
  });
}

// --- chat: a real Claude Code session --------------------------------------
//
// This is not the local worker (that one still exists behind /api/chat and is
// what the Telegram bridge talks to). This continues the SAME Claude Code
// session Felix has at his desk, which is what he asked for: "ich will genau
// in dem chat hier weiterschreiben von meinem handy aus". The transcript is
// the real one, read off disk; sending resumes the session by id.

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
let chatInFlight = false;
let chatSession = null;   // { id, title, ... }

function addBubble(text, cls) {
  const div = document.createElement("div");
  div.className = `bubble ${cls}`;
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}

function renderTranscript(data) {
  chatLog.innerHTML = "";
  if (!data.messages || !data.messages.length) {
    chatLog.innerHTML = `<div class="empty-state">Diese Sitzung ist leer.</div>`;
    return;
  }
  if (data.total_messages > data.messages.length) {
    const more = document.createElement("button");
    more.className = "chip";
    more.style.alignSelf = "center";
    more.textContent = `${data.total_messages - data.messages.length} ältere laden`;
    more.addEventListener("click", () => openSession(data.session_id, (data.shown_turns || 14) + 20));
    chatLog.appendChild(more);
  }
  // Runs of tool calls are folded into one line. A coding session is mostly
  // machine steps - the transcript above was 20 screens of "⚙ Bash: cat >"
  // with the conversation buried in it. The steps are still there, one tap
  // away, because sometimes the step IS the answer ("did it actually run
  // the migration?").
  let run = [];
  const flushRun = () => {
    if (!run.length) return;
    const items = run;
    run = [];
    if (items.length === 1) { addBubble(items[0], "tool"); return; }
    const el = addBubble(`⚙ ${items.length} Schritte — antippen`, "tool");
    el.style.cursor = "pointer";
    let open = false;
    el.addEventListener("click", () => {
      open = !open;
      el.textContent = open ? items.join("\n") : `⚙ ${items.length} Schritte — antippen`;
    });
  };
  for (const m of data.messages) {
    if (m.tool) { run.push(m.text); continue; }
    flushRun();
    addBubble(m.text, m.role === "user" ? "me" : "bot");
  }
  flushRun();
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function openSession(sessionId, limit) {
  const bar = document.getElementById("chat-session");
  bar.querySelector(".session-title").textContent = "lädt…";
  try {
    const data = await api("/api/claude-transcript", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId || "", limit: limit || 14 }),
    });
    setConnDot("ok");
    if (!data.session_id) {
      chatLog.innerHTML = `<div class="empty-state">${escapeHtml(data.error || "keine Sitzung")}</div>`;
      return;
    }
    chatSession = { id: data.session_id, title: data.title, stats: data.stats };
    localStorage.setItem(SESSION_KEY, data.session_id);
    bar.querySelector(".session-title").textContent = data.title || data.session_id.slice(0, 8);
    bar.querySelector(".session-meta").textContent =
      `${data.total_messages} · $${usd(data.stats?.usd)}`;
    renderTranscript(data);
  } catch (err) {
    setConnDot("err");
    chatLog.innerHTML = `<div class="empty-state">Fehler: ${escapeHtml(err.message)}</div>`;
  }
}

async function loadChat() {
  // No session remembered: the server picks the most recently written one,
  // which is "immer vom letzten genutzten chat" - open the app and you are
  // where you left off without choosing anything.
  await openSession(localStorage.getItem(SESSION_KEY) || "");
}

document.getElementById("chat-session").addEventListener("click", async () => {
  if (window.fxTap) window.fxTap();
  openSheet(`<div class="hint">Wird geladen…</div>`);
  try {
    const d = await api("/api/claude-sessions");
    openSheet(d.sessions.map((s) => `
      <button class="sheet-item ${s.id === chatSession?.id ? "on" : ""}" data-sid="${s.id}">
        <span style="flex:1;min-width:0">
          <span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
            ${escapeHtml(s.title)}${s.active ? " ·  läuft gerade" : ""}</span>
          <span class="si-sub" style="margin:0">${s.messages} Nachrichten · ${ago(s.updated_ago)} · $${usd(s.stats.usd)}</span>
        </span>
      </button>`).join("") || `<div class="empty-state">Keine Sitzungen gefunden.</div>`,
      (root) => root.querySelectorAll(".sheet-item").forEach((el) =>
        el.addEventListener("click", () => {
          closeSheet();
          openSession(el.dataset.sid);
        })));
  } catch (err) {
    openSheet(`<div class="empty-state">Fehler: ${escapeHtml(err.message)}</div>`);
  }
});

// Backs off from 1.5s to 6s. A Claude turn on a large session is minutes,
// not seconds, so a tight poll would be thousands of pointless requests.
async function pollClaude(jobId, bubble) {
  const started = Date.now();
  let wait = 1500;
  for (;;) {
    await new Promise((r) => setTimeout(r, wait));
    wait = Math.min(wait * 1.3, 6000);
    let res;
    try {
      res = await api("/api/claude-result", {
        method: "POST", body: JSON.stringify({ job_id: jobId }),
      });
    } catch (err) {
      // A failed poll is not a failed answer - the phone may have lost the
      // tailnet for a moment. Keep trying; the result is on disk either way.
      bubble.textContent = `… (offline? ${Math.round((Date.now() - started) / 1000)}s)`;
      continue;
    }
    if (res.ready) return res;
    if (res.lost) throw new Error(res.error || "Job verloren");
    // Showing the count is the point: "still thinking, 40s" reads as slow,
    // a frozen "…" reads as broken.
    bubble.textContent = `denkt nach … ${res.elapsed ?? 0}s`;
  }
}

chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, window.innerHeight * 0.3)}px`;
});
chatInput.addEventListener("keydown", (e) => {
  // Enter sends on a hardware keyboard, newline on a phone: shift+Enter is
  // not reachable on a touch keyboard, so on a phone Enter has to be able to
  // make a paragraph.
  if (e.key === "Enter" && !e.shiftKey && window.matchMedia("(pointer: fine)").matches) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (chatInFlight || !chatSession) return;
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  chatInput.style.height = "auto";
  addBubble(text, "me");
  const pending = addBubble("denkt nach …", "bot pending");
  chatInFlight = true;
  document.getElementById("chat-send").disabled = true;
  try {
    const queued = await api("/api/claude-send", {
      method: "POST",
      body: JSON.stringify({ session_id: chatSession.id, message: text }),
    });
    setConnDot("ok");
    const res = await pollClaude(queued.job_id, pending);
    pending.textContent = res.reply || (res.ok ? "(keine Antwort)" : res.error || "fehlgeschlagen");
    pending.className = `bubble bot${res.ok ? "" : " err"}`;
    if (res.usd) {
      const cost = document.createElement("div");
      cost.className = "bubble tool";
      cost.textContent = `$${usd(res.usd)} · ${Math.round((res.duration_ms || 0) / 1000)}s`;
      chatLog.appendChild(cost);
    }
    chatLog.scrollTop = chatLog.scrollHeight;
    refreshCostPill();
  } catch (err) {
    pending.textContent = `Fehler: ${err.message}`;
    pending.className = "bubble bot err";
    setConnDot("err");
  } finally {
    chatInFlight = false;
    document.getElementById("chat-send").disabled = false;
  }
});

// --- device control --------------------------------------------------------

let deviceState = { id: null, list: [], width: 1080, height: 2400, live: false,
                    actions: [], rooted: false };

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
      stopStream();
      deviceState.id = el.dataset.dev;
      loadDevices();
    }));

    const dev = deviceState.list.find((d) => d.id === deviceState.id) || {};
    if (!dev.reachable) {
      infoEl.innerHTML = `<span>${escapeHtml(dev.reason || "nicht erreichbar")}</span>`;
      document.getElementById("device-stage").innerHTML = `<div class="stage-empty">offline</div>`;
      document.getElementById("device-stagebar").innerHTML = "";
      document.getElementById("device-controls").innerHTML = "";
      document.getElementById("device-tools").innerHTML = "";
      return;
    }
    deviceState.width = dev.width || 1080;
    deviceState.height = dev.height || 2400;
    deviceState.actions = dev.actions || [];
    deviceState.rooted = !!dev.rooted;
    const b = dev.battery || {};
    infoEl.innerHTML = `<span>${b.level ?? "?"}%${b.charging ? " lädt" : ""}</span>
      <span>${dev.screen_on ? "Bildschirm an" : "Bildschirm aus"}</span>
      <span>${escapeHtml(dev.current_app || "—")}</span>
      <span>${dev.rooted ? "root" : "ohne root"}</span>
      <span>${deviceState.width}×${deviceState.height}</span>`;
    renderStageBar();
    renderDeviceControls();
    renderDeviceTools();
    loadNodeRunner();
    startStream();
  } catch (err) {
    setConnDot("err");
    infoEl.innerHTML = `<span>Fehler: ${escapeHtml(err.message)}</span>`;
  }
}

// --- live picture ----------------------------------------------------------
//
// An <img> pointed at a multipart/x-mixed-replace response: the browser keeps
// the connection open and swaps the frame every time one arrives. Measured
// end to end, median 0.47s from an input to seeing it - against 1.1-1.4s for
// a single screenshot before, with nothing at all in between them. See
// scripts/phone_stream.py for how the frames are produced.
//
// The token travels in the query string here and nowhere else in this app:
// an <img> request carries no Authorization header and there is no way to
// give it one.

function stageEl() { return document.getElementById("device-stage"); }

function stageBadge(text, live) {
  const el = document.getElementById("stage-badge");
  if (el) { el.textContent = text; el.classList.toggle("live", !!live); }
}

// The stage is sized from the phone's own aspect ratio, and both pictures -
// the still and the live one - are laid over each other inside it. Without a
// fixed shape the box collapses to nothing until the first frame arrives,
// which is exactly when it needs to look like a phone.
function prepareStage() {
  const stage = stageEl();
  stage.style.aspectRatio = `${deviceState.width} / ${deviceState.height}`;
  stage.innerHTML = `<div class="stage-badge" id="stage-badge">…</div>
    <img id="dev-still" class="layer" alt="">
    <img id="dev-img" class="layer live" alt="Bildschirm">`;
  return stage;
}

function startStream() {
  prepareStage();
  deviceState.live = true;
  stageBadge("verbinde…", false);
  const img = document.getElementById("dev-img");
  img.src = `/device-stream?device=${encodeURIComponent(deviceState.id)}`
          + `&token=${encodeURIComponent(getToken())}&t=${Date.now()}`;
  img.addEventListener("error", () => {
    // The stream could not start - ffmpeg missing, adb gone, phone away.
    // Fall back to the single screenshot rather than showing nothing: slow
    // is still a picture, and the badge says which one you are looking at.
    deviceState.live = false;
    renderStageBar();
    refreshStill();
  });
  bindStageTaps(img);
  renderStageBar();
  deviceSay("");

  // A still underneath, fetched once. It is what you see while the video
  // starts up - and it is the ONLY thing you see when the phone's display is
  // off, because a dark screen composites no frames at all and screenrecord
  // has nothing to encode. That case looked like a broken panel: a black box
  // with a green LIVE badge on it.
  refreshStill(true);

  // Chrome fires `load` on a multipart image only when the whole stream
  // ends, so the arrival of the first frame has to be observed rather than
  // listened for.
  clearInterval(deviceState.watch);
  const startedAt = Date.now();
  deviceState.watch = setInterval(() => {
    if (!deviceState.live) { clearInterval(deviceState.watch); return; }
    const el = document.getElementById("dev-img");
    if (!el) { clearInterval(deviceState.watch); return; }
    if (el.naturalWidth > 0) {
      el.classList.add("on");
      stageBadge("live", true);
      clearInterval(deviceState.watch);
      return;
    }
    if (Date.now() - startedAt > 6000) {
      // Still nothing. Say why, and offer the one button that fixes it.
      stageBadge("Bildschirm aus", false);
      if (!document.getElementById("stage-wake")) {
        const b = document.createElement("button");
        b.id = "stage-wake";
        b.className = "chip stage-wake";
        b.textContent = "Handy wecken";
        b.addEventListener("click", async (e) => {
          e.stopPropagation();
          b.textContent = "…";
          await deviceAction({ action: "key", key: "wake" });
          b.remove();
          startStream();
        });
        stageEl().appendChild(b);
      }
    }
  }, 400);
}

function stopStream() {
  deviceState.live = false;
  clearInterval(deviceState.watch);
  const img = document.getElementById("dev-img");
  // Clearing src is what actually closes the HTTP connection, which is what
  // lets the server-side stream notice it has no viewers and shut ffmpeg and
  // screenrecord down.
  if (img) img.src = "";
  if (deviceState.id) {
    api("/api/device-action", {
      method: "POST",
      body: JSON.stringify({ device: deviceState.id, action: "stream_stop" }),
    }).catch(() => {});
  }
}

function bindStageTaps(img) {
  const send = async (e, kind) => {
    const rect = img.getBoundingClientRect();
    const x = Math.round(((e.clientX - rect.left) / rect.width) * deviceState.width);
    const y = Math.round(((e.clientY - rect.top) / rect.height) * deviceState.height);
    if (window.fxTap) window.fxTap();
    showTapRipple(e.clientX - rect.left, e.clientY - rect.top);
    const t = await deviceAction({ action: kind, x, y });
    if (!t.ok) deviceSay(t.error, true);
    // No refresh call: the stream shows the result on its own. That single
    // change is most of what "zu langsam" was - every tap used to be
    // followed by a second-and-a-half of waiting for a new still.
    if (!deviceState.live) refreshStill();
  };
  let down = null;
  img.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY, t: Date.now() }; });
  img.addEventListener("pointerup", async (e) => {
    if (!down) return;
    const dx = e.clientX - down.x, dy = e.clientY - down.y;
    const rect = img.getBoundingClientRect();
    // A drag on the picture is a swipe on the phone. Without it the panel
    // could tap but not scroll, which makes most apps unusable remotely.
    if (Math.hypot(dx, dy) > 18) {
      const sx = Math.round(((down.x - rect.left) / rect.width) * deviceState.width);
      const sy = Math.round(((down.y - rect.top) / rect.height) * deviceState.height);
      const ex = Math.round(((e.clientX - rect.left) / rect.width) * deviceState.width);
      const ey = Math.round(((e.clientY - rect.top) / rect.height) * deviceState.height);
      const r = await deviceAction({ action: "swipe", x1: sx, y1: sy, x2: ex, y2: ey,
                                     ms: Math.max(80, Math.min(Date.now() - down.t, 800)) });
      if (!r.ok) deviceSay(r.error, true);
      if (!deviceState.live) refreshStill();
    } else {
      await send(e, "tap");
    }
    down = null;
  });
}

function showTapRipple(x, y) {
  const wrap = stageEl();
  if (!wrap) return;
  const dot = document.createElement("span");
  dot.className = "tap-ripple";
  dot.style.left = `${x}px`;
  dot.style.top = `${y}px`;
  wrap.appendChild(dot);
  // Removed by timer, not by animationend: if the image is replaced
  // mid-animation that event never fires and the marker would stay forever.
  setTimeout(() => dot.remove(), 650);
}

async function refreshStill(asBackdrop) {
  if (!asBackdrop) { prepareStage(); stageBadge("Standbild", false); }
  if (!asBackdrop) deviceSay("Bildschirm holen…");
  try {
    const r = await deviceAction({ action: "screenshot" });
    if (!r.ok) { if (!asBackdrop) deviceSay(r.error, true); return; }
    deviceState.width = r.width || deviceState.width;
    deviceState.height = r.height || deviceState.height;
    // Fetched as a blob with the auth header, not set as a plain src: an
    // <img> request carries no Authorization header, so the gated endpoint
    // answers 401 and the browser shows a broken image.
    const res = await fetch(r.url, { headers: { Authorization: `Bearer ${getToken()}` } });
    if (!res.ok) { if (!asBackdrop) deviceSay(`Bild ${res.status}`, true); return; }
    const blob = await res.blob();
    // Revoke the previous one: a screenshot every few seconds would otherwise
    // leak a megabyte at a time for as long as the panel stays open.
    if (deviceState.blobUrl) URL.revokeObjectURL(deviceState.blobUrl);
    deviceState.blobUrl = URL.createObjectURL(blob);
    const target = document.getElementById(asBackdrop ? "dev-still" : "dev-img");
    if (!target) return;
    target.src = deviceState.blobUrl;
    target.classList.add("on");
    if (!asBackdrop) { bindStageTaps(target); deviceSay(""); }
  } catch (err) {
    if (!asBackdrop) deviceSay(err.message, true);
  }
}

function renderStageBar() {
  const el = document.getElementById("device-stagebar");
  el.innerHTML = `
    <button class="chip ${deviceState.live ? "on" : ""}" id="st-live">Live</button>
    <button class="chip ${deviceState.live ? "" : "on"}" id="st-still">Standbild</button>
    ${deviceState.actions.includes("record")
      ? `<button class="chip" id="st-rec">8s aufnehmen</button>` : ""}`;
  el.querySelector("#st-live").addEventListener("click", () => {
    if (deviceState.live) return;
    startStream();
  });
  el.querySelector("#st-still").addEventListener("click", () => {
    stopStream();
    renderStageBar();
    refreshStill();
  });
  el.querySelector("#st-rec")?.addEventListener("click", async () => {
    deviceSay("nimmt auf …");
    const r = await deviceAction({ action: "record", seconds: 8 });
    deviceSay(r.ok ? `gespeichert: ${r.file.name} (Dateien)` : r.error, !r.ok);
  });
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
      <button class="chip" data-key="enter">Enter</button>
    </div>
    <div class="inline-form">
      <input id="dev-text" type="text" placeholder="Text aufs Handy tippen…" autocomplete="off">
      <button class="pill-btn" id="dev-send">Senden</button>
    </div>`;
  el.querySelectorAll("[data-key]").forEach((b) => b.addEventListener("click", async () => {
    if (window.fxTap) window.fxTap();
    const r = await deviceAction({ action: "key", key: b.dataset.key });
    if (!r.ok) { deviceSay(r.error, true); return; }
    if (!deviceState.live) refreshStill();
  }));
  const send = async () => {
    const input = document.getElementById("dev-text");
    if (!input.value.trim()) return;
    const r = await deviceAction({ action: "text", text: input.value });
    input.value = "";
    deviceSay(r.ok ? "" : r.error, !r.ok);
    if (!deviceState.live) refreshStill();
  };
  el.querySelector("#dev-send").addEventListener("click", send);
  el.querySelector("#dev-text").addEventListener("keydown", (e) => {
    if (e.key === "Enter") send();
  });
}

// --- the rooted toolkit ----------------------------------------------------
//
// phone_root.py has had all of this since it was written - SMS, call log,
// clipboard, filesystem, packages, settings, a root shell - and none of it
// was reachable from the app, which only ever exposed screenshot/tap/key.
// Each entry names the action api.py allows; the panel only shows the ones
// the selected device actually reported, so the unrooted phone does not
// offer buttons that can only fail.

const TOOLS = [
  { id: "info", label: "Gerät", run: (r) => kv(r.info, { root: r.root ? "ja" : "nein" }) },
  { id: "notifications", label: "Meldungen", run: (r) => lines(r.notifications,
      (n) => [`${(n.package || "").split(".").pop()} · ${n.title || ""}`, n.text || ""]) },
  { id: "sms", label: "SMS", run: (r) => lines(r.messages,
      (m) => [`${m.address || "?"}`, m.body || ""], (m) => m.date || "") },
  { id: "calls", label: "Anrufe", run: (r) => lines(r.calls,
      (c) => [`${c.number || "?"}`, `${c.type || ""} ${c.duration ?? ""}`], (c) => c.date || "") },
  { id: "clipboard", label: "Zwischenablage", run: (r) => `<pre class="out">${escapeHtml(r.clipboard || "(leer)")}</pre>` },
  { id: "apps", label: "Apps", run: (r, ctx) => appList(r, ctx) },
  { id: "ls", label: "Dateien", run: (r, ctx) => fileList(r, ctx), arg: "path", argDefault: "/sdcard" },
  { id: "shell", label: "Shell", run: (r) => `<pre class="out">${escapeHtml(r.output || "(keine Ausgabe)")}</pre>`,
    arg: "command", argPlaceholder: "z.B. df -h" },
];

function kv(obj, extra) {
  const all = { ...(obj || {}), ...(extra || {}) };
  return `<div class="kv">${Object.entries(all)
    .map(([k, v]) => `<div><b>${escapeHtml(k)}</b> ${escapeHtml(String(v))}</div>`).join("")}</div>`;
}

function lines(items, main, when) {
  if (!items || !items.length) return `<div class="empty-state">nichts da</div>`;
  return items.map((it) => {
    const [head, tail] = main(it);
    return `<div class="list-line">
      <span><span class="who">${escapeHtml(head)}</span> ${escapeHtml(String(tail).slice(0, 120))}</span>
      ${when ? `<span class="when">${escapeHtml(String(when(it)))}</span>` : ""}
    </div>`;
  }).join("");
}

function appList(r) {
  return `<div class="hint">${r.total} Apps</div>` + (r.apps || []).map((p) => `
    <div class="list-line"><span class="who">${escapeHtml(p)}</span>
      <button class="chip" data-open="${escapeHtml(p)}">öffnen</button></div>`).join("");
}

function fileList(r) {
  return `<div class="hint">${escapeHtml(r.path)}</div>` + (r.entries || []).map((n) => `
    <div class="list-line"><span>${escapeHtml(n)}</span>
      <span>
        <button class="chip" data-cd="${escapeHtml(r.path.replace(/\/$/, "") + "/" + n)}">öffnen</button>
        <button class="chip" data-pull="${escapeHtml(r.path.replace(/\/$/, "") + "/" + n)}">holen</button>
      </span></div>`).join("");
}

function renderDeviceTools() {
  const el = document.getElementById("device-tools");
  const hint = document.getElementById("device-tools-hint");
  const available = TOOLS.filter((t) => deviceState.actions.includes(t.id));
  hint.textContent = deviceState.rooted
    ? "Volles Root-Werkzeug: alles was phone_root.py kann, direkt hier."
    : "Ohne root ist nur ein Teil möglich — der Rest braucht das gerootete Handy.";
  el.innerHTML = available.map((t) =>
    `<button class="chip" data-tool="${t.id}">${escapeHtml(t.label)}</button>`).join("")
    + (deviceState.rooted ? `<button class="chip danger" data-tool="_danger">Gefährlich…</button>` : "");
  el.querySelectorAll("[data-tool]").forEach((b) => b.addEventListener("click", () => {
    if (window.fxTap) window.fxTap();
    el.querySelectorAll(".chip").forEach((c) => c.classList.remove("on"));
    b.classList.add("on");
    if (b.dataset.tool === "_danger") return renderDangerPanel();
    runTool(TOOLS.find((t) => t.id === b.dataset.tool));
  }));
  document.getElementById("device-toolpanel").innerHTML = "";
}

async function runTool(tool, argValue) {
  const panel = document.getElementById("device-toolpanel");
  const value = argValue !== undefined ? argValue : (tool.argDefault || "");
  panel.innerHTML = (tool.arg ? `
    <div class="inline-form">
      <input id="tool-arg" type="text" value="${escapeHtml(value)}"
             placeholder="${escapeHtml(tool.argPlaceholder || "")}"
             autocomplete="off" autocapitalize="off" spellcheck="false">
      <button class="pill-btn" id="tool-go">Los</button>
    </div>` : "") + `<div class="hint">läuft…</div>`;
  const wireArg = () => {
    const go = () => runTool(tool, document.getElementById("tool-arg").value);
    panel.querySelector("#tool-go")?.addEventListener("click", go);
    panel.querySelector("#tool-arg")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") go();
    });
  };
  wireArg();
  if (tool.arg && !value) { panel.querySelector(".hint").textContent = "Wert eingeben."; return; }
  const payload = { action: tool.id };
  if (tool.arg) payload[tool.arg] = value;
  try {
    const r = await deviceAction(payload);
    const body = r.ok ? tool.run(r, { value }) : `<div class="empty-state">${escapeHtml(r.error)}</div>`;
    panel.innerHTML = (tool.arg ? `
      <div class="inline-form">
        <input id="tool-arg" type="text" value="${escapeHtml(value)}"
               placeholder="${escapeHtml(tool.argPlaceholder || "")}"
               autocomplete="off" autocapitalize="off" spellcheck="false">
        <button class="pill-btn" id="tool-go">Los</button>
      </div>` : "") + body;
    wireArg();
    // Sub-actions inside a tool's own output: opening an app, walking into a
    // directory, pulling a file down to the Dateien tab.
    panel.querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", async () => {
      const res = await deviceAction({ action: "open", package: b.dataset.open });
      deviceSay(res.ok ? `${b.dataset.open} geöffnet` : res.error, !res.ok);
    }));
    panel.querySelectorAll("[data-cd]").forEach((b) => b.addEventListener("click", () =>
      runTool(tool, b.dataset.cd)));
    panel.querySelectorAll("[data-pull]").forEach((b) => b.addEventListener("click", async () => {
      b.textContent = "…";
      const res = await deviceAction({ action: "pull", path: b.dataset.pull });
      b.textContent = res.ok ? "geholt" : "Fehler";
      deviceSay(res.ok ? `${res.file.name} liegt unter Dateien` : res.error, !res.ok);
    }));
  } catch (err) {
    panel.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

// Destructive verbs are here rather than absent, because it is Felix's phone
// and he asked for a toolkit without restrictions. What they are NOT is one
// tap away: phone_root.py refuses each of them without confirm=true, and this
// is the only place that sends it - after a second, deliberate press.
function renderDangerPanel() {
  const panel = document.getElementById("device-toolpanel");
  panel.innerHTML = `
    <p class="hint">Jede dieser Aktionen braucht zwei Klicks. Sie sind
      absichtlich unbequem — ein Fehlgriff kostet dich Daten oder die App.</p>
    <div class="inline-form">
      <input id="dg-arg" type="text" placeholder="Paket oder Pfad" autocomplete="off"
             autocapitalize="off" spellcheck="false">
    </div>
    <div class="chip-row">
      <button class="chip danger" data-dg="uninstall" data-field="package">App löschen</button>
      <button class="chip danger" data-dg="wipe" data-field="package">App-Daten löschen</button>
      <button class="chip danger" data-dg="rm" data-field="path">Datei löschen</button>
      <button class="chip danger" data-dg="reboot" data-field="">Neustart</button>
    </div>
    <p class="hint" id="dg-status"></p>`;
  panel.querySelectorAll("[data-dg]").forEach((b) => {
    let armed = false;
    const label = b.textContent;
    b.addEventListener("click", async () => {
      if (!armed) {
        armed = true;
        b.textContent = "wirklich?";
        b.classList.add("on");
        setTimeout(() => { armed = false; b.textContent = label; b.classList.remove("on"); }, 4000);
        return;
      }
      armed = false;
      b.textContent = label;
      b.classList.remove("on");
      const payload = { action: b.dataset.dg, confirm: true };
      if (b.dataset.field) payload[b.dataset.field] = document.getElementById("dg-arg").value.trim();
      const r = await deviceAction(payload);
      document.getElementById("dg-status").textContent =
        r.ok ? (r.output || "erledigt") : r.error;
      document.getElementById("dg-status").style.color = r.ok ? "var(--good)" : "var(--bad)";
    });
  });
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
  out.textContent = `[${nodeState.id}] wird eingereiht…`;
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
      out.textContent = `[${nodeState.id}] ${res.state}…`;
    }
  } catch (err) {
    out.textContent = `Fehler: ${err.message}`;
  }
}

// --- costs -----------------------------------------------------------------

async function refreshCostPill() {
  const pill = document.getElementById("cost-pill");
  try {
    const d = await api("/api/costs");
    const o = d.openrouter || {};
    if (o.live) {
      pill.textContent = `$${usd(o.balance_usd)}`;
      pill.classList.toggle("warn", Number(o.balance_usd) < 2);
    } else {
      pill.textContent = "—";
    }
  } catch (err) {
    pill.textContent = "—";
  }
}
document.getElementById("cost-pill").addEventListener("click", () => switchTo("screen-costs"));

async function loadCosts() {
  const heroEl = document.getElementById("cost-hero");
  const cardsEl = document.getElementById("cost-cards");
  const claudeEl = document.getElementById("cost-claude");
  const callsEl = document.getElementById("cost-calls");
  const noteEl = document.getElementById("cost-claude-note");
  heroEl.innerHTML = `<div class="balance"><div class="cap">lädt</div></div>`;
  try {
    const d = await api("/api/costs");
    setConnDot("ok");
    const o = d.openrouter || {};
    const c = d.claude || {};

    // One number, big, and it is the one that can run out. Everything else on
    // this screen is context for it.
    const bal = Number(o.balance_usd ?? 0);
    const low = bal < 2;
    heroEl.innerHTML = `
      <div class="balance">
        <div class="cap">OpenRouter-Guthaben</div>
        <div class="amount ${low ? "low" : ""}">${o.live ? "$" + usd(bal) : "—"}</div>
        <div class="sub">${o.live
          ? `von $${usd(o.credits_usd)} aufgeladen · $${usd(o.used_usd)} verbraucht`
          : escapeHtml(o.error || "nicht abrufbar")}</div>
        <a class="topup" href="${escapeHtml(o.topup_url)}" target="_blank" rel="noopener noreferrer">
          Guthaben aufladen</a>
        <div class="meter ${o.month_spent_usd / o.budget_usd > 0.8 ? "warn" : ""}">
          <i style="width:${Math.min(100, (o.month_spent_usd / (o.budget_usd || 1)) * 100).toFixed(1)}%"></i>
        </div>
        <div class="sub" style="margin:10px 0 0">
          Monatslimit: $${usd(o.month_spent_usd)} von $${usd(o.budget_usd)} —
          $${usd(o.budget_left_usd)} übrig</div>
      </div>`;

    const u = o.usage || {};
    cardsEl.innerHTML = `
      <div class="signals">
        <div class="signal"><span class="v">$${usd(u.today)}</span><span class="k">heute</span></div>
        <div class="signal"><span class="v">$${usd(u.week)}</span><span class="k">7 Tage</span></div>
        <div class="signal"><span class="v">$${usd(u.month)}</span><span class="k">Monat</span></div>
      </div>
      <div class="card">
        <div class="row"><h3>Bezahltes Modell</h3>
          <span class="sub">${o.paid_enabled ? "an" : "aus"}</span></div>
        <div class="sub">${escapeHtml(o.paid_model || "—")}</div>
      </div>
      ${Object.entries(o.months || {}).map(([m, v]) => `
        <div class="card"><div class="row"><h3>${escapeHtml(m)}</h3>
          <span class="sub">$${usd(v)}</span></div></div>`).join("")}`;

    // Deliberately separated and labelled. These are not charges - the chat
    // runs on Felix's Claude subscription. Presenting an estimate next to a
    // real prepaid balance without saying which is which would be the most
    // misleading thing this screen could do.
    noteEl.textContent = c.note || "";
    claudeEl.innerHTML = `
      <div class="signals">
        <div class="signal warn"><span class="v">$${usd(c.month_usd)}</span><span class="k">diesen Monat</span></div>
        <div class="signal"><span class="v">$${usd(c.total_usd)}</span><span class="k">insgesamt</span></div>
      </div>
      ${(c.sessions || []).slice(0, 8).map((s) => `
        <div class="card">
          <div class="row"><h3>${escapeHtml(s.id.slice(0, 8))}</h3>
            <span class="sub">$${usd(s.usd)}</span></div>
          <div class="sub">${s.turns} Antworten · ${ago(s.updated_ago)}</div>
        </div>`).join("")}`;

    const calls = o.calls || [];
    callsEl.innerHTML = calls.length ? `<table>
      <tr><th>Wann</th><th>Modell</th><th class="num">USD</th></tr>
      ${calls.map((k) => `<tr>
        <td>${escapeHtml((k.ts || "").replace("T", " ").slice(5, 16))}</td>
        <td>${escapeHtml((k.model || "").split("/").pop())}</td>
        <td class="num">${usd(k.usd)}</td></tr>`).join("")}</table>`
      : `<div class="empty-state">Noch keine bezahlten Aufrufe protokolliert.</div>`;

    litPanels(document.getElementById("screen-costs"));
    if (window.fxReveal) window.fxReveal(cardsEl, ".card", 40);
  } catch (err) {
    setConnDot("err");
    heroEl.innerHTML = `<div class="empty-state">Fehler: ${escapeHtml(err.message)}</div>`;
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
    if (s.letters_sent !== undefined) pills.push([s.letters_sent, "Briefe raus"]);
    if (s.leads_qualified !== undefined) pills.push([s.leads_qualified, "qualifiziert"]);
    // Qualified and mailable are different numbers - only the overlap with an
    // OSM postal address can receive a letter. Showing the bigger one alone
    // overstates what a batch can actually reach.
    if (s.leads_mailable !== undefined) pills.push([s.leads_mailable, "mit Postadresse"]);
    if (s.flips && s.flips.open) pills.push([s.flips.open, "Flips offen"]);
    signalsEl.innerHTML = pills.map(([v, k]) =>
      `<div class="signal"><span class="v">${v}</span><span class="k">${escapeHtml(k)}</span></div>`).join("");

    if (!data.actions.length) {
      cardsEl.innerHTML = `<div class="empty-state">Nichts offen — alles erledigt.</div>`;
      return;
    }
    cardsEl.innerHTML = data.actions.map((a) => `
      <div class="card">
        <div class="row">
          <h3>${a.gates ? "ZUERST" : a.euros ? "~" + a.euros + " EUR" : "Basis"}</h3>
          <span class="sub">${a.minutes} min</span>
        </div>
        <div class="sub" style="color:var(--text);margin:6px 0">${escapeHtml(a.action)}</div>
        <div class="sub">${escapeHtml(a.note)}</div>
      </div>`).join("");
    litPanels(cardsEl);
    if (window.fxReveal) window.fxReveal(cardsEl, ".card", 45);
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
    summaryEl.innerHTML = `
      <div class="signal"><span class="v">${data.total_qualified}</span><span class="k">qualifiziert</span></div>
      <div class="signal"><span class="v">${data.leads.length}</span><span class="k">gezeigt</span></div>`;
    if (!data.leads.length) {
      tableEl.innerHTML = `<div class="empty-state">Noch keine Leads.</div>`;
      return;
    }
    tableEl.innerHTML = `<div class="cards">` + data.leads.map((l) => `
      <div class="card">
        <div class="row"><h3>${escapeHtml(l.name || l.domain)}</h3>
          <span class="sub">Score ${l.score ?? "?"}</span></div>
        <div class="sub">${escapeHtml(l.domain)}</div>
        <div class="sub" style="margin-top:6px;opacity:.75">
          ${escapeHtml(dmarcFinding(l))}
          ${l.provider ? " · " + escapeHtml(l.provider) : ""}
          ${l.address?.city ? " · " + escapeHtml(l.address.city) : ""}
          ${l.phone ? " · " + escapeHtml(l.phone) : ""}
        </div>
      </div>`).join("") + `</div>`;
    litPanels(tableEl);
  } catch (err) {
    setConnDot("err");
    tableEl.innerHTML = `<div class="empty-state">Fehler beim Laden: ${escapeHtml(err.message)}</div>`;
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
      method: "POST", body: JSON.stringify(snipeFilters),
    });
    setConnDot("ok");

    // Tier chips show UNFILTERED totals - what exists, not what survived the
    // current filter. A chip that reads "S 0" because S is filtered out would
    // be telling you the opposite of the truth.
    const counts = data.tier_counts || {};
    filtersEl.innerHTML = `
      ${TIER_ORDER.filter((t) => counts[t]).map((t) =>
        `<button class="chip ${snipeFilters.tier === t ? "on" : ""}" data-tier="${t}">${t} · ${counts[t]}</button>`).join("")}
      ${(data.watches || []).map((w) =>
        `<button class="chip ${snipeFilters.watch === w ? "on" : ""}" data-watch="${escapeHtml(w)}">${escapeHtml(w)}</button>`).join("")}
      <button class="chip ${snipeFilters.max_distance === 15 ? "on" : ""}" data-dist="15">≤15 km</button>
      <button class="chip ${snipeFilters.max_price === 30 ? "on" : ""}" data-price="30">≤30 €</button>
      <button class="chip clear">zurücksetzen</button>`;

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
    listEl.innerHTML = `<div class="cards">` + data.snipes.map((s) => {
      const price = s.price === 0 ? "zu verschenken"
        : (s.price === null || s.price === undefined ? "kein Preis" : s.price + " €");
      const dist = s.distance === null || s.distance === undefined ? "im Ort" : s.distance + " km";
      return `<a class="card" style="display:block;text-decoration:none;color:inherit"
                 href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer">
          <div class="row"><h3>${escapeHtml(s.title)}</h3>
            <span class="sub" style="color:var(--gold)">${escapeHtml(s.tier)}</span></div>
          <div class="sub">${escapeHtml(price)} · ${escapeHtml(dist)} · ${escapeHtml(s.watch || "")}</div>
          <div class="sub" style="margin-top:6px;opacity:.7">${escapeHtml((s.reasons || []).join(" · "))}</div>
        </a>`;
    }).join("") + `</div>`;
    litPanels(listEl);
    if (window.fxReveal) window.fxReveal(listEl, ".card", 35);
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
    tableEl.innerHTML = `<div class="cards">` + data.rows.map((r) => {
      const net = parseFloat((r["Net €"] || "").replace(",", "."));
      const color = r.open ? "var(--text-dim)" : (net < 0 ? "var(--bad)" : "var(--good)");
      return `<div class="card">
          <div class="row"><h3>${escapeHtml(r.Item || "")}</h3>
            <span class="sub" style="color:${color}">
              ${r.open ? "offen" : `${escapeHtml(r["Net €"] || "")} €`}</span></div>
          <div class="sub">${escapeHtml(r.Date || "")} · ${escapeHtml(r.Category || "")}
            · Kauf ${escapeHtml(r["Buy €"] || "?")} €
            ${!r.open && r["€/hour"] ? " · " + escapeHtml(r["€/hour"]) + " €/h" : ""}</div>
        </div>`;
    }).join("") + `</div>`;
    litPanels(tableEl);
  } catch (err) {
    setConnDot("err");
    tableEl.innerHTML = `<div class="empty-state">Fehler beim Laden: ${escapeHtml(err.message)}</div>`;
  }
}

// --- files -----------------------------------------------------------------

async function downloadFile(url, name, btn) {
  // Fetched as a blob with the auth header, not linked to directly - the
  // token never appears in a URL or browser history this way, and
  // server.py gates /downloads/* on exactly this header.
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "…";
  try {
    const res = await fetch(url, { headers: { "Authorization": `Bearer ${getToken()}` } });
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
    ? `${done} hochgeladen, ${failed.length} fehlgeschlagen — ${failed.join("; ")}`
    : `${done} Datei(en) hochgeladen.`;
  statusEl.style.color = failed.length ? "var(--bad)" : "var(--good)";
  loadUploads();
}

function updateUploadButton() {
  const input = document.getElementById("upload-input");
  document.getElementById("upload-send").disabled = !(input.files || []).length;
}

// Both uploads and downloads are already sorted newest-first by the server,
// so capping here always keeps the most recent items visible. Purely
// client-side: the full list already arrived in one request, so "show more"
// just reveals more of what is already in memory.
const LIST_PAGE_SIZE = 20;

function renderCapped(listEl, items, toHtml, opts = {}) {
  const pageSize = opts.pageSize || LIST_PAGE_SIZE;
  let shown = pageSize;
  const render = () => {
    const visible = items.slice(0, shown);
    const remaining = items.length - visible.length;
    listEl.innerHTML = visible.map(toHtml).join("") + (remaining > 0
      ? `<button class="pill-btn ghost wide" id="list-show-more">Mehr anzeigen (${remaining})</button>`
      : "");
    if (opts.afterRender) opts.afterRender(listEl);
    litPanels(listEl);
    document.getElementById("list-show-more")?.addEventListener("click", () => {
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
        <div class="row"><h3>${escapeHtml(f.name)}</h3></div>
        <div class="sub">${formatBytes(f.size)} · ${escapeHtml(f.modified.replace("T", " "))}</div>
      </div>`);
  } catch (err) {
    listEl.innerHTML = `<div class="empty-state">Fehler: ${escapeHtml(err.message)}</div>`;
  }
}

async function buildVoiceProfile() {
  const btn = document.getElementById("voice-build");
  const statusEl = document.getElementById("voice-status");
  btn.disabled = true;
  statusEl.style.color = "";
  statusEl.textContent = "Baue Profil…";
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
      listEl.innerHTML = `<div class="empty-state">Noch keine Dateien.</div>`;
      return;
    }
    renderCapped(listEl, data.files, (f) => `
      <div class="card">
        <div class="row">
          <h3>${escapeHtml(f.name)}</h3>
          <button class="chip" data-url="${escapeHtml(f.url)}" data-name="${escapeHtml(f.name)}">laden</button>
        </div>
        <div class="sub">${formatBytes(f.size)} · ${escapeHtml(f.modified.replace("T", " "))}</div>
      </div>`, {
      // Re-wired after every render, including "show more" clicks, since
      // renderCapped replaces innerHTML each time - listeners on the
      // previous DOM nodes are gone with them.
      afterRender: (el) => el.querySelectorAll("[data-url]").forEach((btn) => {
        btn.addEventListener("click", () => downloadFile(btn.dataset.url, btn.dataset.name, btn));
      }),
    });
  } catch (err) {
    setConnDot("err");
    listEl.innerHTML = `<div class="empty-state">Fehler beim Laden: ${escapeHtml(err.message)}</div>`;
  }
}

// --- wiring ----------------------------------------------------------------

document.getElementById("upload-input").addEventListener("change", updateUploadButton);
document.getElementById("upload-send").addEventListener("click", sendSelectedUploads);
document.getElementById("voice-build").addEventListener("click", buildVoiceProfile);
document.getElementById("node-send")?.addEventListener("click", runOnNode);
document.getElementById("node-cmd")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runOnNode();
});

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
window.addEventListener("appinstalled", () =>
  document.getElementById("install-btn").classList.add("hidden"));

// A backgrounded tab must not keep a phone's screen recording open.
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopStream();
  else if (currentScreen === "screen-devices") startStream();
});
window.addEventListener("pagehide", stopStream);

// --- boot ------------------------------------------------------------------

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

bootstrapTokenFromUrl();

if (!getToken()) {
  showTokenModal();
} else {
  loadActiveScreen();
}
