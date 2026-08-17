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
  createRoot(el).render(<BlurText as={tag} text={text} />);
});
