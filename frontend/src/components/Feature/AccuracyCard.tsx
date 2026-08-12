import ProgressBar from "./ProgressBar";
import { PROGRESS } from "./features.data";

export default function AccuracyCard() {
    return (
        <div
            className="
          w-full
          overflow-hidden
          rounded-[28px]
          md:rounded-[34px]
          bg-gradient-to-br
          from-[#050814]
          via-[#04111a]
          to-[#03150f]
          p-5
          sm:p-6
          md:p-8
          shadow-[0_25px_80px_rgba(0,0,0,0.25)]
        "
        >
            <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-zinc-600"></p>

            <div className="mt-6 md:mt-8 flex items-end">
                <span
                    className="
            font-mono
            font-black
            text-white
            text-5xl
            sm:text-6xl
            lg:text-7xl
          "
                >
                    98
                </span>

                <span
                    className="
            ml-1
            mb-2
            md:mb-3
            font-mono
            text-zinc-500
            text-lg
            md:text-xl
          "
                >
                    .2%
                </span>
            </div>

            <div
                className="
          mt-6
          md:mt-8
          inline-flex
          items-center
          rounded-full
          border
          border-emerald-500/20
          bg-emerald-500/10
          px-3
          md:px-4
          py-2
        "
            >
                <span
                    className="
            font-mono
            text-[10px]
            sm:text-xs
            font-semibold
            text-emerald-400
          "
                >
                    ↖ +1.4% vs_prev_month
                </span>
            </div>

            <div className="mt-14">
                <p className="mb-8 font-mono text-[11px] uppercase tracking-[0.25em] text-zinc-600"></p>

                {PROGRESS.map((item) => (
                    <ProgressBar key={item.name} item={item} />
                ))}
            </div>
        </div>
    );
}
