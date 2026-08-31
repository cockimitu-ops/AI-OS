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
};

function loadActiveScreen() {
  const active = document.querySelector(".screen.active");
  const loader = SCREEN_LOADERS[active.id];
  if (loader) loader();
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.screen).classList.add("active");
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
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, thread_id: getThreadId() }),
    });
    pending.textContent = data.reply;
    pending.className = "bubble assistant";
    setConnDot("ok");
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
    const rows = data.leads.map((l) => `
      <tr>
        <td>${escapeHtml(l.name || l.domain)}</td>
        <td>${escapeHtml(l.domain)}</td>
        <td>${l.score ?? ""}</td>
        <td>${escapeHtml(dmarcFinding(l))}</td>
        <td>${escapeHtml(l.provider || "")}</td>
        <td>${l.address ? escapeHtml(l.address.city) : ""}</td>
        <td>${escapeHtml(l.phone || "")}</td>
      </tr>
    `).join("");
    tableEl.innerHTML = `<table>
      <thead><tr><th>Name</th><th>Domain</th><th>Score</th><th>Befund</th><th>Provider</th><th>Ort</th><th>Telefon</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  } catch (err) {
    setConnDot("err");
    tableEl.innerHTML = `<div class="empty-state">Fehler beim Laden: ${escapeHtml(err.message)}</div>`;
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
    const rows = data.rows.map((r) => {
      const net = parseFloat((r["Net €"] || "").replace(",", "."));
      const cls = r.open ? "open" : (net < 0 ? "loss" : "win");
      return `
        <tr class="${cls}">
          <td>${escapeHtml(r.Date || "")}</td>
          <td>${escapeHtml(r.Item || "")}</td>
          <td>${escapeHtml(r.Category || "")}</td>
          <td>${escapeHtml(r["Buy €"] || "")}</td>
          <td>${r.open ? "offen" : escapeHtml(r["Sold €"] || "")}</td>
          <td class="net">${escapeHtml(r["Net €"] || "")}</td>
          <td>${escapeHtml(r["€/hour"] || "")}</td>
        </tr>`;
    }).join("");
    tableEl.innerHTML = `<table>
      <thead><tr><th>Datum</th><th>Item</th><th>Kategorie</th><th>Kauf €</th><th>Verkauft €</th><th>Netto €</th><th>€/h</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
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
    listEl.innerHTML = data.files.map((f) => `
      <div class="card">
        <div class="card-action">${escapeHtml(f.name)}</div>
        <div class="download-meta">${formatBytes(f.size)} · ${escapeHtml(f.modified.replace("T", " "))}</div>
      </div>
    `).join("");
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
    listEl.innerHTML = data.files.map((f) => `
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
    `).join("");
    listEl.querySelectorAll(".download-btn").forEach((btn) => {
      btn.addEventListener("click", () =>
        downloadFile(btn.dataset.url, btn.dataset.name, btn));
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
