// AI-OS web client. Vanilla JS, no framework or build step - this is a
// handful of screens fetching JSON, not an app that needs one. Every
// dashboard section here is a plain HTML render, not a markdown dump -
// that distinction is the whole reason this project exists.

const TOKEN_KEY = "aios_web_token";
const THREAD_KEY = "aios_thread_id";

function getToken() { return localStorage.getItem(TOKEN_KEY) || ""; }
function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }

function getThreadId() {
  let id = localStorage.getItem(THREAD_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(THREAD_KEY, id);
  }
  return id;
}
function newThreadId() {
  const id = crypto.randomUUID();
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

document.getElementById("token-save").addEventListener("click", () => {
  const val = document.getElementById("token-input").value.trim();
  if (!val) return;
  setToken(val);
  hideTokenModal();
  loadActiveScreen();
});

// --- tabs --------------------------------------------------------------

const SCREEN_LOADERS = {
  "screen-money": loadMoneyBoard,
  "screen-dmarc": loadDmarcLeads,
  "screen-flips": loadFlipLog,
  "screen-downloads": loadDownloads,
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
    if (s.leads_qualified !== undefined) pills.push(`${s.leads_qualified} Leads bereit`);
    if (s.flips && s.flips.open) pills.push(`${s.flips.open} Flips offen (${s.flips.capital_tied_up.toFixed(0)} EUR gebunden)`);
    signalsEl.innerHTML = pills.map((p) => `<span class="signal-pill">${escapeHtml(p)}</span>`).join("");

    if (!data.actions.length) {
      cardsEl.innerHTML = `<div class="empty-state">Nichts offen - alles erledigt.</div>`;
      return;
    }
    cardsEl.innerHTML = data.actions.map((a) => `
      <div class="card">
        <div class="card-top">
          <span class="card-euros">${a.euros ? "~" + a.euros + " EUR" : "Basis"}</span>
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

// --- boot ------------------------------------------------------------------

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

if (!getToken()) {
  showTokenModal();
} else {
  loadActiveScreen();
}
