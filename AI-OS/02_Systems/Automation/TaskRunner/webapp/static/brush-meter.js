// Small progress canvases share the painting's bristles, not its render loop.
(() => {
  "use strict";
  const meters = new Map();
  const fractionOf = value => {
    const n = Number(value);
    return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : 0;
  };
  const resize = typeof ResizeObserver === "function"
    ? new ResizeObserver(entries => entries.forEach(entry => draw(entry.target))) : null;

  function draw(canvas) {
    const state = meters.get(canvas);
    if (!state) return;
    const width = canvas.clientWidth, height = canvas.clientHeight || 8;
    if (width <= 0) return; // Hidden tabs are repainted when ResizeObserver sees them.
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const end = width * state.fraction;
    if (end === 0) return;
    const theme = getComputedStyle(canvas);
    let color = state.color || theme.getPropertyValue("--accent").trim() || "#6c8870";
    if (Array.isArray(color)) color = `rgb(${color.slice(0, 3).map(n => Math.max(0, Math.min(255, Number(n) || 0))).join(",")})`;
    const variable = typeof color === "string" && color.match(/^var\((--[\w-]+)\)$/);
    if (variable) color = theme.getPropertyValue(variable[1]).trim() || "#6c8870";
    ctx.strokeStyle = color;
    ctx.lineCap = "butt";
    // Fixed bristle lengths keep a repeated render from looking like movement.
    const tips = [0, .76, .23, 1, .42, .88, .16];
    for (let i = 0; i < tips.length; i++) {
      const y = (i + .5) * height / tips.length;
      const tip = Math.max(0, end - Math.min(5, end * .15) * tips[i]);
      ctx.lineWidth = height / tips.length * (i % 2 ? .70 : .96);
      ctx.globalAlpha = .75 + (i % 3) * .10;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.quadraticCurveTo(tip * .52, y + (i % 2 ? .36 : -.36), tip, y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  function paintMeter(canvas, fraction, color) {
    if (!canvas || typeof canvas.getContext !== "function") return;
    const first = !meters.has(canvas);
    const value = fractionOf(fraction);
    meters.set(canvas, {fraction: value, color});
    canvas.classList.add("brush-meter");
    if (!canvas.hasAttribute("aria-hidden")) {
      canvas.setAttribute("role", "progressbar");
      canvas.setAttribute("aria-valuemin", "0");
      canvas.setAttribute("aria-valuemax", "100");
      canvas.setAttribute("aria-valuenow", String(Math.round(value * 100)));
      if (!canvas.hasAttribute("aria-label")) canvas.setAttribute("aria-label", "Nutzung");
    }
    if (first && resize) resize.observe(canvas);
    draw(canvas);
  }

  function refresh(root = document) {
    for (const canvas of meters.keys()) {
      if (!canvas.isConnected) {
        if (resize) resize.unobserve(canvas);
        meters.delete(canvas);
      }
    }
    const legacy = [...root.querySelectorAll(".meter")];
    if (root.matches?.(".meter")) legacy.unshift(root);
    legacy.forEach(meter => {
      if (meter.tagName === "CANVAS") return;
      const ink = meter.querySelector("i");
      if (!ink) return;
      let canvas = meter.querySelector("canvas.brush-meter");
      if (!canvas) {
        canvas = document.createElement("canvas");
        canvas.setAttribute("aria-hidden", "true");
        meter.appendChild(canvas);
      }
      meter.classList.add("painted-meter");
      const fraction = fractionOf(parseFloat(ink.style.width) / 100);
      meter.setAttribute("role", "progressbar");
      meter.setAttribute("aria-valuemin", "0");
      meter.setAttribute("aria-valuemax", "100");
      meter.setAttribute("aria-valuenow", String(Math.round(fraction * 100)));
      if (!meter.hasAttribute("aria-label")) meter.setAttribute("aria-label", "Nutzung");
      paintMeter(canvas, fraction, meter.classList.contains("warn") ? "var(--bad)" : "var(--accent)");
    });
  }

  let scheduled = null;
  function schedule() {
    if (scheduled !== null) return;
    scheduled = requestAnimationFrame(() => { scheduled = null; refresh(); });
  }
  new MutationObserver(schedule).observe(document.body, {childList: true, subtree: true});
  new MutationObserver(() => {
    refresh();
    for (const canvas of meters.keys()) draw(canvas);
  }).observe(document.body, {attributes: true, attributeFilter: ["data-light"]});
  if (!resize) window.addEventListener("resize", () => {
    refresh();
    for (const canvas of meters.keys()) draw(canvas);
  });
  window.paintMeter = window.fxPaintMeter = paintMeter;
  window.fxRefreshMeters = refresh;
  refresh();
})();
