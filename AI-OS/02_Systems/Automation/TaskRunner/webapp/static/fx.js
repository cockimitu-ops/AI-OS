// Atmosphere layer for AI-OS: the drifting particle field, the dither grain,
// and the entrance choreography.
//
// Two references drive this, both Felix's: "Can You Grasp Time" (Dogan Ural) -
// a black void with a subject made of luminous filaments and starlight - and
// efecto.app, a dither/ASCII art tool whose whole look is heavy monochrome
// grain over a particle form. The brief was literally "unnötig viel Design",
// so this leans in: real moving particles with parallax depth, a grain layer
// on top of everything, a light sweep across the hero, numbers that count up,
// and staggered entrances.
//
// The constraints that keep "excessive" from meaning "bad":
//
//   * It pauses completely when the tab is hidden. An animation loop running
//     in a backgrounded PWA all day is a battery bug wearing a costume.
//   * prefers-reduced-motion turns off ALL motion - particles stop drifting
//     (they still render as a static field, so the design survives), sweeps
//     and entrances become instant. Motion sensitivity is not a preference
//     to override for decoration.
//   * Device pixel ratio is capped at 2. Felix's phone reports 2.75; that is
//     ~90% more pixels to fill every frame for a field of soft dots nobody
//     can resolve at that density anyway.
//   * Particle count scales with viewport area, so a phone does not get a
//     laptop's workload.
//
// No dependencies, no build step - same as the rest of static/.

(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // --- the particle field --------------------------------------------------

  const canvas = document.getElementById("fx-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d", { alpha: true });

  let W = 0, H = 0, dpr = 1;
  let particles = [];
  let rafId = null;
  let lastFrame = 0;

  // Three depth bands. Far particles are small, dim and slow; near ones are
  // larger, brighter and drift faster. That difference is the whole illusion
  // of depth - a single uniform layer reads as flat noise, which is exactly
  // what the previous CSS-gradient starfield looked like on a real phone.
  // Density and brightness were tuned up hard after seeing the first version
  // rendered: it was technically present and visually forgettable, which is
  // the opposite of the brief. Roughly 2.5x the particles, brighter across
  // every band, and a fourth "bokeh" band of a few big soft out-of-focus
  // motes - the depth cue that stops a particle field reading as flat noise.
  const BANDS = [
    { count: 0.000190, r: [0.4, 1.0],  speed: [1.5, 4],   alpha: [0.25, 0.55], hue: "far"   },
    { count: 0.000105, r: [0.9, 1.9],  speed: [4, 9],     alpha: [0.5, 0.85],  hue: "mid"   },
    { count: 0.000034, r: [1.5, 3.0],  speed: [9, 17],    alpha: [0.7, 1.0],   hue: "near"  },
    { count: 0.0000045, r: [5, 11],    speed: [14, 24],   alpha: [0.05, 0.11], hue: "bokeh" },
  ];

  // Palette straight off the reference: mostly cool white-blue filaments,
  // with gold and violet as rare specks - never as fills.
  function pickColor(band) {
    const roll = Math.random();
    if (band === "bokeh") {
      return roll < 0.4 ? [185, 160, 255] : (roll < 0.7 ? [232, 201, 138] : [150, 190, 255]);
    }
    if (band === "near" && roll < 0.2) return [232, 201, 138];   // gold
    if (roll < 0.1) return [185, 160, 255];                       // violet
    if (roll < 0.58) return [207, 227, 255];                      // filament blue
    return [255, 255, 255];
  }

  function rand(range) { return range[0] + Math.random() * (range[1] - range[0]); }

  function build() {
    particles = [];
    const area = W * H;
    for (const band of BANDS) {
      const n = Math.round(area * band.count);
      for (let i = 0; i < n; i++) {
        particles.push({
          x: Math.random() * W,
          y: Math.random() * H,
          r: rand(band.r),
          // Drift is upward and slightly sideways - dust rising through a
          // shaft of light, matching the reference's trail direction rather
          // than falling snow.
          vy: -rand(band.speed) / 60,
          vx: (Math.random() - 0.5) * rand(band.speed) / 220,
          a: rand(band.alpha),
          color: pickColor(band.hue),
          // Each particle twinkles on its own slow cycle; a shared phase
          // would make the whole field pulse in unison, which reads as a
          // flicker bug rather than starlight.
          phase: Math.random() * Math.PI * 2,
          twinkle: 0.25 + Math.random() * 0.9,
        });
      }
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
    build();
  }

  function draw(now) {
    const dt = lastFrame ? Math.min((now - lastFrame) / 16.67, 3) : 1;
    lastFrame = now;
    ctx.clearRect(0, 0, W, H);

    for (const p of particles) {
      if (!reduceMotion) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.phase += 0.012 * p.twinkle * dt;
        // Wrap rather than respawn: a particle reappearing at a random
        // position is visible as a pop, while wrapping just continues the
        // drift off one edge and back on the other.
        if (p.y < -4) { p.y = H + 4; p.x = Math.random() * W; }
        if (p.x < -4) p.x = W + 4;
        else if (p.x > W + 4) p.x = -4;
      }
      const tw = reduceMotion ? 1 : 0.65 + 0.35 * Math.sin(p.phase);
      const alpha = p.a * tw;
      const [r, g, b] = p.color;

      // The larger particles get a soft halo, which is what makes them read
      // as light sources instead of dots. Only the near band gets it - doing
      // it for every particle is a lot of overdraw for something invisible
      // at 0.5px.
      // Bokeh motes are ONLY their bloom - a hard core would make them read
      // as a smudge on the screen rather than something out of focus.
      const isBokeh = p.r > 4;
      const haloR = isBokeh ? p.r : p.r * 5.5;
      if (p.r > 1.1) {
        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, haloR);
        grad.addColorStop(0, `rgba(${r},${g},${b},${alpha * (isBokeh ? 1 : 0.7)})`);
        grad.addColorStop(isBokeh ? 0.55 : 0.4, `rgba(${r},${g},${b},${alpha * 0.22})`);
        grad.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(p.x, p.y, haloR, 0, Math.PI * 2);
        ctx.fill();
      }
      if (!isBokeh) {
        ctx.fillStyle = `rgba(${r},${g},${b},${alpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Static field under reduced motion: draw once, then stop the loop
    // entirely rather than re-rendering an identical frame 60 times a second.
    if (reduceMotion) { rafId = null; return; }
    rafId = requestAnimationFrame(draw);
  }

  function start() {
    if (rafId === null) { lastFrame = 0; rafId = requestAnimationFrame(draw); }
  }
  function stop() {
    if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
  }

  // A backgrounded PWA must cost nothing. This is the difference between an
  // atmosphere and a battery complaint.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop(); else start();
  });

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    // Debounced: mobile browsers fire resize continuously while the URL bar
    // collapses, and rebuilding the whole field on every one of those frames
    // is a visible stutter during an ordinary scroll.
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { resize(); if (!rafId) start(); }, 180);
  });

  resize();
  start();

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
      const t = Math.min((now - startedAt) / duration, 1);
      // easeOutExpo: fast out of the gate, long settle - reads as decisive
      // rather than as a loading spinner.
      const eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
      el.textContent = String(Math.round(end * eased));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  // A short tap on navigation. Android honours this; iOS ignores it silently,
  // which is the correct no-op rather than something to feature-detect around.
  window.fxTap = function (ms = 8) {
    if (navigator.vibrate) { try { navigator.vibrate(ms); } catch (_) {} }
  };
})();
