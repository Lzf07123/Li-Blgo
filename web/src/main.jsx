import { createRoot } from "react-dom/client";

import AmbientLayer from "./AmbientLayer.jsx";
import BlurText from "./BlurText.jsx";

const density = document.body.dataset.ambient || "none";
if (density !== "none") {
  const host = document.createElement("div");
  host.id = "ambient-root";
  document.body.prepend(host);
  createRoot(host).render(<AmbientLayer density={density} />);
}

document.querySelectorAll("[data-blur]").forEach((el) => {
  const text = el.textContent || "";
  const tag = el.tagName.toLowerCase();
  const className = el.className || "";
  const host = document.createElement("div");
  el.replaceWith(host);
  createRoot(host).render(<BlurText as={tag} text={text} className={className} />);
});

/* 首页聚焦 Hero：下滑时个人介绍整体缩小并淡出（rAF + transform，GPU 合成） */
const heroInner = document.querySelector(".hero-inner");
if (heroInner) {
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduced) {
    let rafId = 0;
    const update = () => {
      rafId = 0;
      const max = window.innerHeight * 0.55;
      const p = Math.min(1, Math.max(0, window.scrollY / max));
      heroInner.style.transform = `scale(${1 - 0.12 * p}) translateY(${-18 * p}px)`;
      heroInner.style.opacity = String(1 - 0.4 * p);
    };
    const onScroll = () => {
      if (!rafId) rafId = window.requestAnimationFrame(update);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    update();
  }
}
