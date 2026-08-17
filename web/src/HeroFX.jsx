import { motion, useScroll, useSpring, useTransform } from "motion/react";
import { useEffect, useRef } from "react";

export default function HeroFX() {
  const ref = useRef(null);
  const movedRef = useRef(false);
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    const inner = document.getElementById("hero-inner");
    if (inner && ref.current && !movedRef.current) {
      movedRef.current = true;
      ref.current.appendChild(inner);
    }
  }, []);

  const { scrollY } = useScroll();
  const smooth = useSpring(scrollY, { stiffness: 110, damping: 28, mass: 0.6 });
  const progress = (v) => Math.min(1, Math.max(0, v / window.innerHeight));
  const scale = useTransform(smooth, (v) => 1 - 0.18 * progress(v));
  const y = useTransform(smooth, (v) => -30 * progress(v));
  const opacity = useTransform(smooth, (v) => 1 - 0.65 * progress(v / 0.75));
  const filter = useTransform(smooth, (v) => `blur(${5 * progress(v)}px)`);

  if (reduced) return <div ref={ref} className="hero-inner" />;
  return (
    <motion.div ref={ref} className="hero-inner" style={{ scale, y, opacity, filter }} />
  );
}
