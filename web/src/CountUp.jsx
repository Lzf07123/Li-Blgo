import { useInView, useMotionValue, useSpring } from "motion/react";
import { useEffect, useRef } from "react";

export default function CountUp({ to, from = 0, duration = 2, separator = "", className = "" }) {
  const ref = useRef(null);
  const value = useMotionValue(from);
  const spring = useSpring(value, { damping: 20 + 40 / duration, stiffness: 100 / duration });
  const inView = useInView(ref, { once: true, margin: "0px" });
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    if (inView && !reduced) value.set(to);
  }, [inView, reduced, to, value]);

  useEffect(() => {
    return spring.on("change", (v) => {
      if (ref.current) ref.current.textContent = Number(v.toFixed(0)).toLocaleString("en-US");
    });
  }, [spring]);

  return <span ref={ref} className={className}>{reduced ? to : from}</span>;
}
