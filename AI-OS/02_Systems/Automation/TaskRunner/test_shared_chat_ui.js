// Offline regression tests: no provider calls, browser storage, or running server.
// Run with: node test_shared_chat_ui.js
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const source = fs.readFileSync(path.join(__dirname, "webapp/static/app.js"), "utf8");
const section = source.slice(source.indexOf("// --- chat:"), source.indexOf("// --- device control"));
assert.ok(section.includes("function sendMessage"), "Chat test boundary must include the sending flow");

function element() {
  return {
    style: {}, dataset: {}, children: [], handlers: {}, classList: { toggle() {} },
    isConnected: true, innerHTML: "", value: "",
    addEventListener(name, fn) { this.handlers[name] = fn; },
    setAttribute() {}, querySelector() { return element(); }, querySelectorAll() { return []; },
    appendChild(child) { this.children.push(child); child.isConnected = true; },
    prepend(child) { this.children.unshift(child); },
    insertBefore(child) { this.children.push(child); }, remove() { this.isConnected = false; },
  };
}

const nodes = new Map();
const storage = new Map([
  ["aios_engine", "google-pro"],
  ["aios_engine_conversations", JSON.stringify({ "google-pro": "legacy-google", claude: "other" })],
]);
const context = vm.createContext({
  console, Date, setTimeout: (fn) => fn(),
  window: { innerHeight: 900, matchMedia: () => ({ matches: false }) },
  document: {
    getElementById(id) { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); },
    createElement: element,
  },
  localStorage: {
    getItem: (key) => storage.get(key) || null,
    setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key),
  },
  SESSION_KEY: "old-session", PENDING_KEY: "pending", getThreadId: () => "thread",
  escapeHtml: (value) => String(value ?? ""), usd: (value) => value || 0, ago: (value) => value,
  setConnDot() {}, refreshCostPill() {}, openSheet() {}, closeSheet() {},
  api: async () => { throw new Error("Unexpected API call"); },
});
vm.runInContext(section, context);
const run = (code) => vm.runInContext(code, context);
let checks = 0;
async function check(name, fn) { await fn(); checks++; console.log(`PASS ${name}`); }

(async () => {
  await check("Legacy selection migrates once and survives engine switching", () => {
    assert.equal(run("activeConversationId()"), "legacy-google");
    run("selectChatEngine('claude')");
    assert.equal(run("activeConversationId()"), "legacy-google");
  });

  context.api = async () => ({ conversation: {
    id: "shared", engine: "google-pro", title: "Shared", messages: [],
    sessions: { claude: { id: "native-claude" } },
  } });
  await check("Cross-engine conversation uses server-owned native session", async () => {
    await run("openConversation('shared')");
    assert.equal(run("activeConversationId()"), "shared");
    assert.equal(run("chatSession.id"), "native-claude");
  });
  await check("New conversation clears the stale native session", async () => {
    await run("createConversation()");
    assert.equal(run("chatSession"), null);
  });
  await check("Conversation picker is not filtered to one engine", async () => {
    let body;
    context.api = async (_url, options) => { body = JSON.parse(options.body); return { conversations: [] }; };
    await run("loadConversationListInto(document.createElement('div'))");
    assert.equal(body.action, "list");
    assert.ok(!("engine" in body));
  });
  await check("Native Claude attach imports before selecting its shared conversation", async () => {
    let attach;
    context.api = async (url, options) => {
      if (url === "/api/claude-transcript") return {
        session_id: "native-two", title: "Native", messages: [], total_messages: 0,
      };
      attach = JSON.parse(options.body);
      return { conversation: { id: "attached" } };
    };
    await run("openSession('native-two')");
    assert.equal(attach.action, "attach");
    assert.equal(attach.engine, "claude");
    assert.equal(attach.session_id, "native-two");
    assert.equal(run("activeConversationId()"), "attached");
  });
  await check("Handoff persists its new ticket before polling again", async () => {
    let calls = 0;
    context.api = async () => {
      if (!calls++) return {
        handed_off: { note: "switched" }, engine: "google-pro", job: "j2", conversation_id: "shared",
      };
      const ticket = JSON.parse(storage.get("pending"));
      assert.equal(ticket.id, "j2");
      assert.equal(ticket.engine, "google-pro");
      assert.equal(ticket.conversation_id, "shared");
      assert.equal(ticket.session, undefined);
      return { ready: true, ok: true, reply: "yes" };
    };
    run("rememberPending({id:'j1',engine:'claude',conversation_id:'shared',session:'claude-only'})");
    const result = await run("pollEngine('claude','j1',document.createElement('div'),'shared')");
    assert.equal(result.engine, "google-pro");
    assert.equal(result.conversation_id, "shared");
  });
  await check("All four engines send one shared id without leaking a native id", async () => {
    run("engineList=['claude','aios','google-pro','codex'].map(id=>({id,label:id,available:true,models:['default'],default_model:'default'}));clearPending()");
    for (const engine of ["claude", "aios", "google-pro", "codex"]) {
      let sent;
      context.api = async (url, options) => {
        if (url === "/api/engine-send") {
          sent = JSON.parse(options.body);
          return { job: "run", engine, conversation_id: "shared" };
        }
        if (url === "/api/engine-result") return {
          ready: true, ok: true, reply: "answer", engine, conversation_id: "shared",
        };
        return { conversation: {
          id: "shared", engine: "claude", title: "Shared", sessions: { claude: { id: "native" } },
          messages: [{ role: "assistant", text: "answer", engine }],
        } };
      };
      run(`selectChatEngine('${engine}')`);
      await run("sendMessage('question')");
      assert.equal(sent.engine, engine);
      assert.equal(sent.conversation_id, "shared");
      assert.equal(sent.session, undefined);
      assert.equal(run("chatInFlight"), false);
      assert.equal(storage.has("pending"), false);
    }
  });
  await check("Reloaded pending result restores its shared conversation and answering engine", async () => {
    let readId;
    context.api = async (url, options) => {
      if (url === "/api/engine-result") return {
        ready: true, ok: true, reply: "done", engine: "google-pro", conversation_id: "resumed",
      };
      readId = JSON.parse(options.body).conversation_id;
      return { conversation: { id: "resumed", title: "Resumed", messages: [] } };
    };
    run("rememberPending({id:'last-job',engine:'claude',conversation_id:'resumed'})");
    await run("resumePending()");
    assert.equal(readId, "resumed");
    assert.equal(run("activeConversationId()"), "resumed");
    assert.equal(run("chatEngine"), "google-pro");
    assert.equal(nodes.get("chat-send").disabled, false);
  });
  await check("In-flight picker and submit cannot change context or erase the draft", async () => {
    let called = false;
    context.api = async () => { called = true; throw new Error("Must be blocked"); };
    run("chatInFlight=true;chatInput.value='keep draft'");
    await run("openEnginePicker()");
    nodes.get("chat-form").handlers.submit({ preventDefault() {} });
    assert.equal(called, false);
    assert.equal(nodes.get("chat-input").value, "keep draft");
    run("chatInFlight=false");
  });
  console.log(`${checks} shared-chat frontend behavior checks passed`);
})().catch((error) => { console.error(error); process.exitCode = 1; });
