// The painted layer for AI-OS.
//
// Felix's references for this pass were five TikToks; he picked Monet, and
// asked for texture everywhere, as elaborate as it gets, with the battery
// explicitly not a consideration ("Fick Akku ich Kauf powerbanks").
//
// WHY THE CANVAS CHANGES WITH THE HOUR
//
// He left light-or-dark to me. Doing both is not a compromise here - it is
// the actual subject. Monet painted the same haystack, the same cathedral
// facade and the same lily pond over and over at different hours, because
// the light was the painting and the object was only its excuse. So this is
// one canvas under four lights: mist at dawn, cream and sage at midday, rose
// and gold at dusk, prussian blue at night. Light in daylight, dark at two
// in the morning, and never two designs.
//
// HOW IT IS PAINTED
//
// Not particles. Broken colour: forty-odd soft blobs of pigment drifting
// over each other at a crawl, composited on a canvas an eighth of the screen
// size and scaled up. The upscale IS the technique - a bilinear stretch of a
// tiny buffer gives exactly the wet, edge-free blending that a hundred
// hand-drawn gradients would cost a phone dearly to produce. It also means
// the whole field costs about as much as a single large gradient per frame.
//
// Over that, motes: dust in a shaft of light rather than stars. Warm, slow,
// few - the previous version's job was to look like a starfield, and this
// one's is to look like air.
//
// The constraints that survive from the previous version, because they were
// never about cost:
//
//   * It pauses completely when the tab is hidden.
//   * prefers-reduced-motion stops all drift; the painting still renders as
//     a still image, which is the correct behaviour for a painting.
//   * Device pixel ratio is capped at 2.
//
// No dependencies, no build step.

(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const canvas = document.getElementById("fx-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d", { alpha: false });

  // --- the light of the hour -----------------------------------------------
  //
  // Each palette is a ground (what the canvas is primed with) and the
  // pigments dragged over it. Kept here rather than in CSS because the paint
  // is drawn, not styled - style.css reads the same names through
  // body[data-light] for everything that is not the canvas.

  const LIGHTS = {
    dawn: {
      ground: [206, 212, 219],
      pigments: [[188, 200, 214], [214, 208, 200], [226, 214, 210],
                 [170, 186, 198], [232, 226, 214], [196, 190, 206]],
      mote: [255, 252, 244], moteAlpha: [0.10, 0.30],
    },
    day: {
      ground: [233, 227, 213],
      pigments: [[168, 184, 154], [127, 163, 195], [226, 214, 186],
                 [205, 213, 190], [240, 233, 216], [186, 176, 200]],
      mote: [255, 250, 232], moteAlpha: [0.14, 0.38],
    },
    dusk: {
      ground: [198, 168, 150],
      pigments: [[226, 178, 140], [166, 132, 158], [232, 201, 138],
                 [140, 122, 150], [216, 158, 130], [180, 168, 190]],
      mote: [255, 236, 200], moteAlpha: [0.16, 0.42],
    },
    night: {
      ground: [22, 27, 43],
      pigments: [[36, 46, 78], [58, 44, 84], [26, 54, 72],
                 [18, 24, 40], [72, 60, 96], [30, 62, 84]],
      mote: [214, 226, 255], moteAlpha: [0.10, 0.34],
    },
  };

  // Boundaries chosen for a person who is regularly awake at two in the
  // morning: night runs long, dawn is short, and dusk starts early enough
  // that a German winter evening is not still rendering midday.
  function lightForHour(h) {
    if (h >= 22 || h < 6) return "night";
    if (h < 9) return "dawn";
    if (h < 17) return "day";
    return "dusk";
  }

  // A light Felix picked by hand, or null for "follow the clock". It has to
  // live here rather than in the caller, because refreshLight() runs every
  // minute and would otherwise paint over a deliberate choice within sixty
  // seconds of it being made.
  let manual = null;
  let light = LIGHTS[lightForHour(new Date().getHours())];
  let lightName = lightForHour(new Date().getHours());

  // --- the paint -----------------------------------------------------------

  // An eighth of the screen. Every pigment blob is drawn here as a hard-edged
  // radial gradient and the browser's own image smoothing does the blending
  // on the way up - which is both cheaper and softer than blurring at full
  // size could ever be.
  const SCALE = 8;
  const paint = document.createElement("canvas");
  const pctx = paint.getContext("2d", { alpha: false });

  let W = 0, H = 0, dpr = 1, pw = 0, ph = 0;
  let blobs = [], motes = [];
  let rafId = null, lastFrame = 0, t = 0;

  function rand(a, b) { return a + Math.random() * (b - a); }

  function buildBlobs() {
    blobs = [];
    // Enough overlapping strokes that no single one is legible as a shape.
    // Below about thirty the eye starts finding circles in it, which is the
    // difference between broken colour and a lava lamp.
    for (let i = 0; i < 42; i++) {
      const c = light.pigments[i % light.pigments.length];
      blobs.push({
        x: Math.random(), y: Math.random(),
        r: rand(0.18, 0.52),
        c,
        a: rand(0.30, 0.72),
        // Two slow oscillators per blob rather than a velocity: paint does
        // not travel in straight lines, and a drift that never repeats keeps
        // the field from developing a visible direction.
        ax: rand(0.02, 0.09), ay: rand(0.02, 0.09),
        px: Math.random() * Math.PI * 2, py: Math.random() * Math.PI * 2,
        sx: rand(0.05, 0.16), sy: rand(0.05, 0.16),
      });
    }
  }

  function buildMotes() {
    motes = [];
    const n = Math.round(W * H * 0.000075);
    for (let i = 0; i < n; i++) {
      motes.push({
        x: Math.random() * W, y: Math.random() * H,
        r: rand(0.6, 2.6),
        a: rand(light.moteAlpha[0], light.moteAlpha[1]),
        vy: -rand(1.5, 7) / 60,
        vx: (Math.random() - 0.5) / 90,
        phase: Math.random() * Math.PI * 2,
        twinkle: 0.2 + Math.random() * 0.7,
      });
    }
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    pw = Math.max(2, Math.ceil(W / SCALE));
    ph = Math.max(2, Math.ceil(H / SCALE));
    paint.width = pw;
    paint.height = ph;
    buildBlobs();
    buildMotes();
  }

  function paintField() {
    const [gr, gg, gb] = light.ground;
    pctx.fillStyle = `rgb(${gr},${gg},${gb})`;
    pctx.fillRect(0, 0, pw, ph);
    for (const b of blobs) {
      const x = (b.x + Math.sin(b.px + t * b.sx) * b.ax) * pw;
      const y = (b.y + Math.cos(b.py + t * b.sy) * b.ay) * ph;
      const r = b.r * Math.max(pw, ph);
      const g = pctx.createRadialGradient(x, y, 0, x, y, r);
      const [cr, cg, cb] = b.c;
      g.addColorStop(0, `rgba(${cr},${cg},${cb},${b.a})`);
      g.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
      pctx.fillStyle = g;
      pctx.fillRect(x - r, y - r, r * 2, r * 2);
    }
  }

  function draw(now) {
    const dt = lastFrame ? Math.min((now - lastFrame) / 16.67, 3) : 1;
    lastFrame = now;
    if (!reduceMotion) t += dt * 0.006;

    paintField();
    ctx.drawImage(paint, 0, 0, pw, ph, 0, 0, W, H);

    const [mr, mg, mb] = light.mote;
    for (const p of motes) {
      if (!reduceMotion) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.phase += 0.010 * p.twinkle * dt;
        // Wrapped rather than respawned: a mote reappearing somewhere new is
        // a visible pop, drifting off one edge and back on the other is not.
        if (p.y < -4) { p.y = H + 4; p.x = Math.random() * W; }
        if (p.x < -4) p.x = W + 4;
        else if (p.x > W + 4) p.x = -4;
      }
      const alpha = p.a * (reduceMotion ? 1 : 0.6 + 0.4 * Math.sin(p.phase));
      const halo = p.r * 4.5;
      const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, halo);
      g.addColorStop(0, `rgba(${mr},${mg},${mb},${alpha})`);
      g.addColorStop(1, `rgba(${mr},${mg},${mb},0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(p.x, p.y, halo, 0, Math.PI * 2);
      ctx.fill();
    }

    // A still painting under reduced motion: rendered once, then the loop
    // stops rather than redrawing an identical frame sixty times a second.
    if (reduceMotion) { rafId = null; return; }
    rafId = requestAnimationFrame(draw);
  }

  function start() {
    if (rafId === null) { lastFrame = 0; rafId = requestAnimationFrame(draw); }
  }
  function stop() {
    if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
  }

  // Repainted when the hour crosses into a different light. Checked rather
  // than scheduled, because a phone that was asleep from midnight to eight
  // never runs a timer set for six.
  function refreshLight() {
    const name = manual || lightForHour(new Date().getHours());
    document.body.dataset.light = name;
    if (name === lightName) return;
    lightName = name;
    light = LIGHTS[name];
    buildBlobs();
    buildMotes();
    if (!rafId) { start(); }
  }
  setInterval(refreshLight, 60000);
  refreshLight();

  // A backgrounded PWA must cost nothing while it is not being looked at -
  // "the battery does not matter" was about how lavish the painting may be,
  // not about burning a phone in a pocket.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { stop(); } else { refreshLight(); start(); }
  });

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    // Debounced: mobile browsers fire resize continuously while the URL bar
    // collapses, and rebuilding the field on every one of those frames is a
    // visible stutter during an ordinary scroll.
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { resize(); if (!rafId) start(); }, 180);
  });

  resize();
  start();

  // Exposed so a screenshot can be taken of any hour without waiting for it.
  // Pick a light by hand, or pass nothing to hand it back to the clock.
  window.fxSetLight = function (name) {
    if (!name || name === "auto") {
      manual = null;
      refreshLight();
      return true;
    }
    if (!LIGHTS[name]) return false;
    manual = name;
    if (name === lightName && document.body.dataset.light === name) return true;
    lightName = name;
    light = LIGHTS[name];
    document.body.dataset.light = name;
    buildBlobs();
    buildMotes();
    if (!rafId) start();
    return true;
  };

  // What is being painted, and whether the clock or Felix decided it.
  window.fxLight = function () {
    return { name: lightName, auto: !manual,
             names: Object.keys(LIGHTS) };
  };

  // --- entrance choreography ----------------------------------------------

  // Elements arrive staggered instead of all at once. Public so the screen
  // renderers can call it after they replace their own innerHTML - which is
  // most of them, so a MutationObserver here would fight the app rather than
  // help it.
  window.fxReveal = function (root, selector, step = 55) {
    if (reduceMotion || !root) return;
    const nodes = root.querySelectorAll(selector);
    nodes.forEach((el, i) => {
      el.classList.add("fx-in");
      el.style.animationDelay = `${i * step}ms`;
    });
  };

  // Numbers count up rather than appearing. On a dashboard whose whole point
  // is "0 Briefe raus", watching a number climb to its value draws the eye to
  // it in a way a static digit does not.
  window.fxCountUp = function (el, target, duration = 900) {
    const end = Number(target) || 0;
    if (reduceMotion || end === 0) { el.textContent = String(end); return; }
    const startedAt = performance.now();
    const tick = (now) => {
      const t2 = Math.min((now - startedAt) / duration, 1);
      // easeOutExpo: fast out of the gate, long settle - reads as decisive
      // rather than as a loading spinner.
      const eased = t2 === 1 ? 1 : 1 - Math.pow(2, -10 * t2);
      el.textContent = String(Math.round(end * eased));
      if (t2 < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  // A short tap on navigation. Android honours this; iOS ignores it silently,
  // which is the correct no-op rather than something to feature-detect around.
  window.fxTap = function (ms = 8) {
    if (navigator.vibrate) { try { navigator.vibrate(ms); } catch (_) {} }
  };
})();
