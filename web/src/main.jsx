import { createRoot } from "react-dom/client";

import AmbientLayer from "./AmbientLayer.jsx";
import BlurText from "./BlurText.jsx";
import HeroFX from "./HeroFX.jsx";

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

/* 首页聚焦 Hero：sticky 吸顶 + 弹簧平滑缩放（motion useScroll/useSpring） */
const hero = document.querySelector(".hero");
const heroInner = document.getElementById("hero-inner");
if (hero && heroInner) {
  const host = document.createElement("div");
  hero.insertBefore(host, heroInner);
  createRoot(host).render(<HeroFX />);
}
