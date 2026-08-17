import { useEffect, useRef } from "react";

const KINDS = ["z", "square", "parallelogram"];
const THEME = {
  dark: { background: [58, 63, 69], stroke: [196, 203, 208], strokeAlpha: 0.55, fillAlpha: 0.04 },
  light: { background: [246, 251, 249], stroke: [90, 105, 100], strokeAlpha: 0.5, fillAlpha: 0.05 },
};

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const rand = (a, b) => a + Math.random() * (b - a);
const lerp = (a, b, t) => a + (b - a) * t;
const rgba = (rgb, alpha) =>
  `rgba(${Math.round(rgb[0])}, ${Math.round(rgb[1])}, ${Math.round(rgb[2])}, ${alpha})`;
const isDarkDocument = () =>
  typeof document !== "undefined" && document.documentElement.classList.contains("dark");

function createShape(kind, index) {
  const layer = index % 3;
  const sizeRange = layer === 0 ? [80, 120] : layer === 1 ? [45, 80] : [30, 45];
  const alphaRange = layer === 0 ? [0.04, 0.07] : layer === 1 ? [0.07, 0.11] : [0.11, 0.15];
  const speedRange = layer === 0 ? [0.15, 0.2] : layer === 1 ? [0.2, 0.28] : [0.28, 0.35];
  return {
    kind,
    x: rand(0.05, 0.95),
    y: rand(0.08, 0.92),
    size: rand(...sizeRange),
    alpha: rand(...alphaRange),
    speed: rand(...speedRange),
    direction: Math.random() < 0.5 ? 1 : -1,
    amplitude: rand(8, 28),
    frequency: rand(0.004, 0.012),
    phase: rand(0, Math.PI * 2),
    lineWidth: rand(1, 1.8),
  };
}

function resolveTheme(theme) {
  if (theme === "auto") return isDarkDocument() ? "dark" : "light";
  return theme;
}

export default function FloatingBackground({
  theme = "auto",
  opacity = 1,
  speed = 1,
  shapeCount = 8,
  transparent = true,
  calm = false,
  scrollWind = true,
  adaptive = true,
}) {
  const canvasRef = useRef(null);
  const optionsRef = useRef({ theme, opacity, speed, shapeCount, transparent, calm, scrollWind, adaptive });
  optionsRef.current = { theme, opacity, speed, shapeCount, transparent, calm, scrollWind, adaptive };
  const shapesRef = useRef([]);
  const paletteRef = useRef({ ...THEME[resolveTheme(theme)], background: [...THEME[resolveTheme(theme)].background], stroke: [...THEME[resolveTheme(theme)].stroke] });
  const calmFactorRef = useRef(calm ? 0.5 : 1);
  const windRef = useRef({ velocity: 0 });
  const mobileRef = useRef(false);
  const autoDarkRef = useRef(isDarkDocument());

  useEffect(() => {
    const rebuildShapes = (count, mobile, adaptiveOn) => {
      const base = clamp(Math.floor(count), 3, 40);
      const limit = adaptiveOn && mobile ? Math.min(base, 6) : base;
      shapesRef.current = Array.from({ length: limit }, (_, i) =>
        createShape(KINDS[i % KINDS.length], i)
      );
    };
    const mobileQuery = window.matchMedia("(max-width: 767px)");
    mobileRef.current = mobileQuery.matches;
    const onMobile = (e) => {
      mobileRef.current = e.matches;
      rebuildShapes(optionsRef.current.shapeCount, e.matches, optionsRef.current.adaptive);
    };
    mobileQuery.addEventListener("change", onMobile);
    rebuildShapes(optionsRef.current.shapeCount, mobileRef.current, optionsRef.current.adaptive);

    const darkObserver = new MutationObserver(() => {
      const next = isDarkDocument();
      if (next !== autoDarkRef.current) {
        autoDarkRef.current = next;
        const colors = THEME[resolveTheme(optionsRef.current.theme)];
        paletteRef.current = {
          background: [...colors.background],
          stroke: [...colors.stroke],
          strokeAlpha: colors.strokeAlpha,
          fillAlpha: colors.fillAlpha,
        };
      }
    });
    darkObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");
    let width = 0;
    let height = 0;
    let raf = 0;
    let resizeTimer = 0;
    let last = performance.now();
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const drawFrame = () => {
      if (!width || !height) return;
      const palette = paletteRef.current;
      const mobileOpacity = optionsRef.current.adaptive && mobileRef.current ? 0.5 : 1;
      const opacityFactor = clamp(optionsRef.current.opacity, 0, 1) * mobileOpacity;
      context.clearRect(0, 0, width, height);
      if (!optionsRef.current.transparent) {
        context.fillStyle = rgba(palette.background, 1);
        context.fillRect(0, 0, width, height);
      }
      for (const shape of shapesRef.current) {
        const x = shape.x * width;
        const y = shape.y * height + Math.sin(shape.phase) * shape.amplitude;
        const half = shape.size / 2;
        const alpha = clamp(shape.alpha * opacityFactor, 0, 1);
        if (alpha < 0.005) continue;
        context.save();
        context.globalAlpha = alpha;
        context.lineWidth = shape.lineWidth;
        context.strokeStyle = rgba(palette.stroke, palette.strokeAlpha);
        context.fillStyle = rgba(palette.stroke, palette.fillAlpha);
        context.beginPath();
        if (shape.kind === "z") {
          context.moveTo(x - half, y - half);
          context.lineTo(x + half, y - half);
          context.lineTo(x - half, y + half);
          context.lineTo(x + half, y + half);
        } else if (shape.kind === "square") {
          context.rect(x - half, y - half, shape.size, shape.size);
        } else {
          const skew = shape.size * 0.4;
          context.moveTo(x - half + skew, y - half);
          context.lineTo(x + half + skew, y - half);
          context.lineTo(x + half, y + half);
          context.lineTo(x - half, y + half);
          context.closePath();
        }
        if (shape.kind !== "z") context.fill();
        context.stroke();
        context.restore();
      }
    };

    const resizeCanvas = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      const tw = Math.round(width * dpr);
      const th = Math.round(height * dpr);
      if (canvas.width !== tw || canvas.height !== th) {
        canvas.width = tw;
        canvas.height = th;
      }
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawFrame();
    };
    const onResize = () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(resizeCanvas, 200);
    };

    const frame = (now) => {
      raf = window.requestAnimationFrame(frame);
      const dt = Math.min(now - last, 100);
      last = now;
      if (reduced || !width) return;
      const units = (dt / 1000) * 60;
      const calmTarget = optionsRef.current.calm ? 0.5 : 1;
      calmFactorRef.current = lerp(calmFactorRef.current, calmTarget, 1 - Math.exp(-dt / 300));
      windRef.current.velocity *= Math.exp(-dt / 250);
      const windFactor = optionsRef.current.scrollWind
        ? Math.min(1.5, Math.max(0.5, 1 - 0.5 * Math.exp(-windRef.current.velocity / 8)))
        : 1;
      const factor = calmFactorRef.current * windFactor * optionsRef.current.speed;
      for (const shape of shapesRef.current) {
        shape.x += (shape.speed * shape.direction * units * factor) / width;
        shape.phase += shape.frequency * units * factor;
        if (shape.x < -0.05) shape.x = 1.05;
        if (shape.x > 1.05) shape.x = -0.05;
      }
      drawFrame();
    };

    resizeCanvas();
    if (reduced) {
      drawFrame();
    } else {
      raf = window.requestAnimationFrame(frame);
    }
    window.addEventListener("resize", onResize);
    let lastY = window.scrollY;
    const onScroll = () => {
      const delta = Math.abs(window.scrollY - lastY);
      lastY = window.scrollY;
      if (delta > 0) windRef.current.velocity = Math.max(windRef.current.velocity, Math.min(delta, 30));
    };
    if (optionsRef.current.scrollWind) {
      window.addEventListener("scroll", onScroll, { passive: true });
    }
    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onScroll);
      mobileQuery.removeEventListener("change", onMobile);
      darkObserver.disconnect();
    };
  }, []);

  return <canvas ref={canvasRef} className="ambient-layer" aria-hidden="true" />;
}
