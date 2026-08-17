"use strict";

/* BlurText 原生移植：data-blur 元素按词错峰从模糊浮现（一次性入场）。
 * reduced-motion 下直接静态渲染。 */
(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const items = document.querySelectorAll("[data-blur]");
  if (!items.length) return;

  items.forEach((el) => {
    const words = el.textContent.trim().split(/\s+/);
    el.textContent = "";
    const spans = words.map((word, i) => {
      const s = document.createElement("span");
      s.className = "blur-word";
      s.textContent = word + (i < words.length - 1 ? " " : "");
      s.style.transitionDelay = `${i * 70}ms`;
      el.appendChild(s);
      return s;
    });
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          spans.forEach((s) => s.classList.add("blur-in"));
          io.disconnect();
        }
      },
      { threshold: 0.3 }
    );
    io.observe(el);
  });
})();
