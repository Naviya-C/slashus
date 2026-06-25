export default function SectionHeader() {
  return (
    <div className="mb-16">
      <div className="mb-5 flex items-center gap-3">
        <div className="h-px w-4 bg-emerald-500" />

        <span className="font-mono text-xs font-bold uppercase tracking-[0.3em] text-emerald-500">
          Features
        </span>
      </div>

      <h2 className="max-w-3xl font-mono text-5xl font-black leading-[1.05] text-black lg:text-6xl">
        Everything you need
        <br />
        to run better assessments.
      </h2>
    </div>
  );
}