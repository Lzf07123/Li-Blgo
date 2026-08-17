"use strict";

/* FloatingBackground Canvas 移植（Li&Chat ambient.js → --liblog-* 令牌）。
 * 纯静态资产，服务器零影响；data-ambient=none 时不启动；
 * reduced-motion 只绘制静态单帧；页面隐藏时暂停。
 */
(function () {
  const densityAttr = (document.body && document.body.dataset.ambient) || "none";
  if (densityAttr === "none") return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const mobileQuery = window.matchMedia("(max-width: 768px)");

  const canvas = document.createElement("canvas");
  canvas.className = "ambient-layer";
  canvas.setAttribute("aria-hidden", "true");
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");

  let width = 0;
  let height = 0;
  let rafId = 0;
  let frameCount = 0;
  let shapes = [];
  let density = densityAttr === "full" ? 8 : 4;
  let colors = { primary: "#25786d", border: "#e1ece8", muted: "#64736c" };
  let wind = 1;
  let lastScrollTop = 0;
  let lastScrollAt = 0;

  function readColors() {
    const css = getComputedStyle(document.documentElement);
    colors = {
      primary: css.getPropertyValue("--liblog-primary").trim(),
      border: css.getPropertyValue("--liblog-border").trim(),
      muted: css.getPropertyValue("--liblog-muted").trim(),
    };
  }

  function buildShapes() {
    const cap = mobileQuery.matches ? Math.min(6, density) : density;
    const kinds = ["line", "square", "z", "dot"];
    shapes = [];
    for (let i = 0; i < cap; i += 1) {
      const size = 14 + ((i * 17) % 42);
      shapes.push({
        kind: kinds[i % kinds.length],
        x: ((i + 1) / (cap + 1)) * width,
        y: 40 + ((i * 97) % Math.max(60, height - 80)),
        size,
        speed: mobileQuery.matches ? 6 + (i % 3) * 3 : 10 + (i % 4) * 6,
        phase: (i / cap) * Math.PI * 2 + ((i * 37) % 20) / 10,
        alpha: 0.04 + (i % 4) * 0.02,
      });
    }
  }

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    buildShapes();
  }

  function drawShape(shape, t, factor) {
    ctx.globalAlpha = shape.alpha;
    ctx.strokeStyle = colors.primary;
    ctx.fillStyle = colors.primary;
    ctx.lineWidth = 1.5;
    ctx.lineCap = "round";
    if (shape.kind === "square") {
      const x = shape.x + Math.sin(t * shape.speed * factor * 0.004 + shape.phase) * 60;
      const y = shape.y + Math.sin(t * shape.speed * factor * 0.002 + shape.phase) * 24;
      ctx.strokeRect(x, y, shape.size, shape.size);
    } else if (shape.kind === "line") {
      const x = ((t * shape.speed * factor + shape.x) % (width + 240)) - 120;
      const y = shape.y + Math.sin(t * shape.speed * factor * 0.003 + shape.phase) * 18;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + 90, y);
      ctx.stroke();
    } else if (shape.kind === "z") {
      const x = ((t * shape.speed * factor * 0.7 + shape.x) % (width + 240)) - 120;
      const y = shape.y + Math.sin(t * shape.speed * factor * 0.002 + shape.phase) * 14;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + 28, y);
      ctx.lineTo(x + 28, y + 18);
      ctx.lineTo(x + 56, y + 18);
      ctx.stroke();
    } else {
      const cx = width * (0.15 + ((shape.phase / (Math.PI * 2)) % 1) * 0.7);
      const cy = height * 0.45;
      const angle = t * shape.speed * factor * 0.002 + shape.phase;
      ctx.beginPath();
      ctx.arc(
        cx + Math.cos(angle) * shape.size * 3,
        cy + Math.sin(angle) * shape.size,
        3,
        0,
        Math.PI * 2
      );
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function frame(t) {
    frameCount += 1;
    wind += (1 - wind) * 0.03;
    if (frameCount % 60 === 0) readColors();
    ctx.clearRect(0, 0, width, height);
    const factor = wind;
    for (const shape of shapes) drawShape(shape, t, factor);
    rafId = window.requestAnimationFrame(frame);
  }

  function start() {
    readColors();
    resize();
    if (reduced) {
      frame(0);
      window.cancelAnimationFrame(rafId);
      return;
    }
    rafId = window.requestAnimationFrame(frame);
  }

  window.addEventListener("resize", resize);
  document.addEventListener(
    "scroll",
    (event) => {
      if (!(event.target instanceof Element)) return;
      const top = event.target.scrollTop || 0;
      const now = performance.now();
      const dt = Math.max(16, now - lastScrollAt);
      const velocity = Math.abs(top - lastScrollTop) / dt;
      wind = Math.min(1.5, Math.max(0.5, 1 + velocity * 0.5));
      lastScrollTop = top;
      lastScrollAt = now;
    },
    { capture: true, passive: true }
  );
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      window.cancelAnimationFrame(rafId);
    } else if (!reduced) {
      rafId = window.requestAnimationFrame(frame);
    }
  });

  window.LiBlogAmbient = {
    setDensity(value) {
      density = value;
      buildShapes();
    },
  };

  start();
})();
