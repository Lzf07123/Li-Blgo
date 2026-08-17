const DOTS = [
  { left: "14%", top: "18%", color: "var(--liblog-accent-ice)", delay: "0s" },
  { left: "84%", top: "16%", color: "var(--liblog-accent-lilac)", delay: "2.3s" },
  { left: "9%", top: "70%", color: "var(--liblog-accent-aqua)", delay: "4.3s" },
  { left: "78%", top: "72%", color: "var(--liblog-accent-sage)", delay: "1.3s" },
  { left: "47%", top: "11%", color: "var(--liblog-accent-mint)", delay: "5.7s" },
  { left: "36%", top: "86%", color: "var(--liblog-accent-sand)", delay: "7s" },
  { left: "64%", top: "58%", color: "var(--liblog-accent-aqua)", delay: "3.3s" },
  { left: "24%", top: "44%", color: "var(--liblog-accent-ice)", delay: "8.3s" },
];

export default function TechAmbience({ soft = false }) {
  return (
    <div className={`tech-ambience${soft ? " tech-ambience--soft" : ""}`} aria-hidden="true">
      <div className="tech-grid" />
      {!soft && (
        <>
          <div className="tech-beam" />
          <div className="tech-beam tech-beam--violet" />
          <div className="tech-beam tech-beam--sage" />
        </>
      )}
      {DOTS.map((dot, index) => (
        <span
          key={index}
          className="tech-dot"
          style={{ left: dot.left, top: dot.top, animationDelay: dot.delay, "--tech-dot-color": dot.color }}
        />
      ))}
    </div>
  );
}
