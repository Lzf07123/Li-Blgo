import { motion } from "motion/react";
import { useEffect, useRef, useState } from "react";

export default function BlurText({
  text,
  as: Tag = "p",
  delay = 70,
  stepDuration = 0.35,
  className = "",
}) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    if (reduced || !ref.current) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold: 0.3 }
    );
    io.observe(ref.current);
    return () => io.disconnect();
  }, [reduced]);

  const words = text.split(/\s+/);
  if (reduced) return <Tag className={className}>{text}</Tag>;

  return (
    <Tag ref={ref} className={className} style={{ display: "flex", flexWrap: "wrap", justifyContent: "center" }}>
      {words.map((word, index) => (
        <motion.span
          key={index}
          className="inline-block"
          initial={{ opacity: 0, filter: "blur(14px)", y: 12, scale: 0.98 }}
          animate={inView ? { opacity: 1, filter: "blur(0px)", y: 0, scale: 1 } : {}}
          transition={{ duration: stepDuration, delay: (index * delay) / 1000, ease: [0.22, 1, 0.36, 1] }}
        >
          {word}
          {index < words.length - 1 ? "\u00A0" : ""}
        </motion.span>
      ))}
    </Tag>
  );
}
