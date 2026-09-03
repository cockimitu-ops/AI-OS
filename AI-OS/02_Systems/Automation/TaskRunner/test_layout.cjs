// Renderer contracts: scheduling and geometry can regress even when JS parses.
// No browser APIs, network calls, real settings or engines are used here.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function environment() {
  const ids = new Map(), frames = new Map(), listeners = new Map();
  const observers = [], intervals = [], strokes = [];
  let frameId = 0, elapsed = 0, hour = 0, minute = 0;
  const makeStyle = () => ({setProperty(name, value) { this[name] = value; }});
  const ctx = new Proxy({
    createImageData: (w, h) => ({data: new Uint8ClampedArray(w * h * 4)}),
    stroke() { strokes.push(this.lineWidth); },
  }, {get: (obj, key) => key in obj ? obj[key] : () => {}});

  class Element {
    constructor(tag) {
      this.tagName = tag.toUpperCase(); this.style = makeStyle(); this.dataset = {};
      this.children = []; this.attrs = new Map(); this.clientWidth = 430; this.clientHeight = 8;
      this.isConnected = true;
      const classes = new Set();
      this.classList = {add: s => classes.add(s), remove: s => classes.delete(s), contains: s => classes.has(s)};
    }
    set innerHTML(value) { this._html = value; this.children = []; }
    get innerHTML() { return this._html ?? String(this.textContent || "").replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
    set id(value) { this._id = value; ids.set(value, this); }
    get id() { return this._id; }
    get nextSibling() {
      return this.parentNode?.children[this.parentNode.children.indexOf(this) + 1] || null;
    }
    appendChild(child) { this.children.push(child); child.parentNode = this; return child; }
    insertBefore(child, before) {
      const index = this.children.indexOf(before);
      this.children.splice(index < 0 ? this.children.length : index, 0, child);
      child.parentNode = this; return child;
    }
    getContext() { return ctx; }
    toDataURL() { return "data:image/png;base64,test"; }
    getBoundingClientRect() { return {bottom: 56}; }
    setAttribute(k, v) { this.attrs.set(k, String(v)); }
    hasAttribute(k) { return this.attrs.has(k); }
    getAttribute(k) { return this.attrs.get(k); }
    addEventListener(k, fn) { this["on" + k] = fn; }
    click() { this.onclick?.(); }
    showModal() { this.open = true; }
    close() { this.open = false; }
    querySelectorAll() { return []; }
    matches() { return false; }
  }
  const body = new Element("body"); body.dataset.screen = "screen-today";
  for (const id of ["fx-canvas", "fx-veil", "fx-grain", "fx-daystrip", "light-btn"]) {
    const element = new Element(id === "fx-canvas" ? "canvas" : "div");
    element.id = id; body.appendChild(element);
  }
  const header = new Element("header");
  const document = {
    body, hidden: false,
    createElement: tag => new Element(tag),
    getElementById: id => ids.get(id) || null,
    querySelector: selector => selector === ".topbar" ? header : null,
    querySelectorAll: () => [],
    addEventListener: (name, fn) => listeners.set("document:" + name, fn),
  };
  class Clock extends Date { getHours() { return hour; } getMinutes() { return minute; } }
  class Observer {
    constructor(fn) { this.fn = fn; observers.push(this); }
    observe(target, options) { this.target = target; this.options = options; }
    unobserve() {}
  }
  const sandbox = {
    document, console, Date: Clock, Math, Uint8ClampedArray,
    navigator: {}, innerWidth: 430, innerHeight: 932, devicePixelRatio: 1,
    matchMedia: () => ({matches: true}),
    performance: {now: () => (elapsed += .025)},
    requestAnimationFrame: fn => { const id = ++frameId; frames.set(id, fn); return id; },
    cancelAnimationFrame: id => frames.delete(id),
    setInterval: fn => { intervals.push(fn); return intervals.length; },
    setTimeout: fn => { fn(); return 1; }, clearTimeout() {},
    MutationObserver: Observer, ResizeObserver: Observer,
    CustomEvent: class { constructor(type) { this.type = type; } },
    addEventListener: (name, fn) => listeners.set(name, fn),
    dispatchEvent: event => listeners.get(event.type)?.(event),
    getComputedStyle: () => ({getPropertyValue: () => "#4a6f4a"}),
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  return {
    sandbox, body, ids, observers, intervals, frames, strokes, Element,
    setTime(h, m = 0) { hour = h; minute = m; intervals[0](); },
    resize(width, height) { sandbox.innerWidth = width; sandbox.innerHeight = height; listeners.get("resize")?.(); },
    frame() { const jobs = [...frames.entries()]; frames.clear(); jobs.forEach(([, fn]) => fn()); },
    screen(name) {
      body.dataset.screen = name;
      observers.filter(o => o.options?.attributeFilter?.includes("data-screen")).forEach(o => o.fn());
    },
  };
}

const env = environment(), fx = env.sandbox;
const scripts = path.join(__dirname, "webapp", "static");
vm.runInContext(fs.readFileSync(path.join(scripts, "fx.js"), "utf8"), fx);

// Midnight belongs three quarters through the dawn-started cycle, not its edge.
assert.equal(parseFloat(env.ids.get("fx-daystrip-mark").style.left), 75);
for (const [hour, light, left] of [[6, "dawn", 0], [9, "day", 12.5], [17, "dusk", 45.833], [22, "night", 66.667]]) {
  env.setTime(hour); assert.equal(fx.fxLight().name, light);
  assert.equal(parseFloat(env.ids.get("fx-daystrip-mark").style.left), left);
}
assert.deepEqual(env.ids.get("fx-daystrip").children.slice(0, 4).map(e => e.style.flex),
  ["3 0 0", "8 0 0", "5 0 0", "8 0 0"]);
let lightSheetOpened = false;
env.ids.get("light-btn").onclick = () => { lightSheetOpened = true; };
env.ids.get("fx-daystrip").click(); assert.ok(lightSheetOpened);

// The renderer itself enforces gate priority even if its caller ranks by money.
fx.fxPlaceObject(1, {action: "Money", euros: 900});
fx.fxPlaceObject(2, {action: "Second", euros: 40});
fx.fxPlaceObject(3, {action: "Blocking", euros: 0, gates: true});
const gate = fx.fxObjectLayout(3), money = fx.fxObjectLayout(1), other = fx.fxObjectLayout(2);
assert.ok(gate.y > money.y && money.y > other.y);
assert.ok(gate.width > money.width && money.width > other.width);
assert.deepEqual(fx.fxObjectLayout(3), gate);
assert.equal(fx.fxPlaceObject(4, {}), null);

// The field reserves actual title/footer space, including wrapped labels on
// the smaller phone. Every light must fit; a dusk horizon is not permission
// for the first label to cover the navigation below it.
fx.fxClearObjects();
fx.fxPlaceObject(1, {action: "Blocking", gates: true});
fx.fxPlaceObject(2, {action: "Second"});
fx.fxPlaceObject(3, {action: "Third"});
for (const [width, height, top, bottom] of [[320, 740, 180, 610], [430, 932, 180, 815]]) {
  env.resize(width, height);
  const labelHeights = {1: 90, 2: 95, 3: 95};
  fx.fxSetFieldBounds({top, bottom, labelHeights});
  for (const light of ["dawn", "day", "dusk", "night"]) {
    fx.fxSetLight(light);
    const layouts = [1, 2, 3].map(rank => fx.fxObjectLayout(rank));
    const blockTop = p => p.y - p.height / 2;
    const blockBottom = p => p.y + p.height / 2 + 8 + labelHeights[p.rank];
    for (const p of layouts) {
      assert.ok(blockTop(p) >= top, `${width}/${light}/rank${p.rank} covers title`);
      assert.ok(blockBottom(p) <= bottom, `${width}/${light}/rank${p.rank} covers footer`);
    }
    assert.ok(layouts[0].y > layouts[1].y && layouts[1].y > layouts[2].y);
    assert.ok(layouts[0].width > layouts[1].width && layouts[1].width > layouts[2].width);
    assert.ok(blockBottom(layouts[1]) <= blockTop(layouts[0]) - 20);
    assert.ok(blockBottom(layouts[2]) <= blockTop(layouts[0]) - 20);
    assert.ok(layouts[1].x + layouts[1].labelWidth / 2 < layouts[2].x - layouts[2].labelWidth / 2);
  }
}
fx.fxClearObjects(); fx.fxSetFieldBounds(null);

// New requests during an unfinished painting must supersede it, not get dropped.
assert.ok(env.frames.size > 0);
env.screen("screen-money"); env.frame();
assert.equal(env.body.dataset.fxScene, "bridge haystacks");
env.screen("screen-command"); env.frame();
assert.equal(env.body.dataset.fxScene, "cathedral spires");
assert.equal(env.body.children.filter(e => e.tagName === "CANVAS").length, 3);
fx.fxSetGrainBoost(Infinity); assert.equal(env.body.style["--grain-boost"], "1");
fx.fxSetGrainBoost(50); assert.equal(env.body.style["--grain-boost"], "2.5");

vm.runInContext(fs.readFileSync(path.join(scripts, "brush-meter.js"), "utf8"), fx);
const meter = new env.Element("canvas");
const before = env.strokes.length;
fx.paintMeter(meter, 0, "var(--accent)"); assert.equal(env.strokes.length, before);
fx.paintMeter(meter, NaN); assert.equal(env.strokes.length, before);
fx.paintMeter(meter, 1.5, "rgb(30, 60, 90)");
assert.equal(env.strokes.length - before, 7);
assert.equal(meter.getAttribute("aria-valuenow"), "100");
assert.equal(meter.width, 430);
meter.clientWidth = 320;
env.observers.filter(o => o.target === meter).forEach(o => o.fn([{target: meter}]));
assert.equal(meter.width, 320);

const inlineScripts = [...fs.readFileSync(path.join(scripts, "today-field-lab.html"), "utf8").matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
for (const match of inlineScripts) {
  new vm.Script(match[1]);
}

async function prototype(data) {
  const test = environment(), browser = test.sandbox;
  for (const id of ["stack", "sub", "rest-btn", "rest-rows", "pipe", "when", "sheet", "close-btn", "action-dialog", "ad-slip", "ad-action", "ad-note", "ad-meta", "ad-close", "ad-gate-label"]) {
    const element = new test.Element("div"); element.id = id; test.body.appendChild(element);
  }
  Object.assign(browser, {
    URLSearchParams, location: {search: "?light=day", pathname: "/today-field-lab.html"},
    localStorage: {getItem: () => "test-only-token"}, history: {replaceState() {}},
    fetch: async () => ({ok: true, status: 200, json: async () => data}),
  });
  vm.runInContext(fs.readFileSync(path.join(scripts, "fx.js"), "utf8"), browser);
  inlineScripts.forEach(match => vm.runInContext(match[1], browser));
  await new Promise(resolve => setImmediate(resolve));
  return test;
}

(async () => {
  // The endpoint supplies three records plus separate counters, not the full
  // action list. Missing records must not turn those five into "nothing left".
  const realShape = await prototype({next_actions: [
    {action: "First", euros: 900, minutes: 20}, {action: "Second", euros: 30, minutes: 10},
    {action: "Blocking", euros: 0, minutes: 5, gates: true},
  ], rest_actions: 5, rest_euros: 125});
  assert.match(realShape.ids.get("rest-btn").textContent, /noch 5 weitere.*125/);
  assert.match(realShape.ids.get("rest-rows").innerHTML, /href="\/\?screen=screen-money"/);
  assert.equal(realShape.ids.get("btn-rank-0").dataset.gate, "true");
  realShape.ids.get("btn-rank-0").click();
  assert.equal(realShape.ids.get("ad-action").textContent, "Blocking");
  assert.equal(realShape.ids.get("action-dialog").open, true);
  const empty = await prototype({next_actions: [], rest_actions: 0, rest_euros: 0});
  assert.equal(empty.ids.get("rest-btn").disabled, true);
  assert.match(empty.ids.get("sub").textContent, /keine Handlung offen/);
  console.log("Layout renderer contracts: OK (time boundaries, gate geometry, active repaint, canvas count, grain bounds, brush resize, real remainder counters, dialog and empty state)");
})().catch(error => { console.error(error); process.exitCode = 1; });
