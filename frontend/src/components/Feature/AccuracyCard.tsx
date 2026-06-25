import ProgressBar from "./ProgressBar";
import { PROGRESS } from "./features.data";

export default function AccuracyCard() {
  return (
    <div className="overflow-hidden rounded-[34px] bg-gradient-to-br from-[#050814] via-[#04111a] to-[#03150f] p-8 shadow-[0_25px_80px_rgba(0,0,0,0.25)]">
      <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-zinc-600">
        // overall_accuracy — last_30_days
      </p>

      <div className="mt-8 flex items-end">
        <span className="font-mono text-7xl font-black text-white">
          98
        </span>

        <span className="mb-3 ml-1 font-mono text-xl text-zinc-500">
          .2%
        </span>
      </div>

      <div className="mt-8 flex h-8 items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4">
        <span className="font-mono text-xs font-semibold text-emerald-400">
          ↖ +1.4% vs_prev_month
        </span>
      </div>

      <div className="mt-14">
        <p className="mb-8 font-mono text-[11px] uppercase tracking-[0.25em] text-zinc-600">
          // scorer_breakdown
        </p>

        {PROGRESS.map((item) => (
          <ProgressBar
            key={item.name}
            item={item}
          />
        ))}
      </div>
    </div>
  );
}