import AuroraBackground from "./AuroraBackground.jsx";
import FloatingBackground from "./FloatingBackground.jsx";
import TechAmbience from "./TechAmbience.jsx";

export default function AmbientLayer({ density }) {
  const full = density === "full";
  return (
    <div className={`ambient ambient-${density}`} aria-hidden="true">
      <AuroraBackground full={full} />
      <TechAmbience soft={!full} />
      <FloatingBackground shapeCount={full ? 8 : 4} />
    </div>
  );
}
