export default function AuroraBackground({ full = true }) {
  const count = full ? 4 : 2;
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className={`aurora aurora-${i + 1}`} />
      ))}
    </>
  );
}
