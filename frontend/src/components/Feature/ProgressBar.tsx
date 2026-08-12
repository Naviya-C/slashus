import type { Progress } from "./types";

interface Props {
    item: Progress;
}

export default function ProgressBar({ item }: Props) {
    return (
        <div
            className="
        mb-4
        grid
        grid-cols-[70px_1fr_35px]
        items-center
        gap-3
        sm:mb-5
        sm:grid-cols-[90px_1fr_40px]
        sm:gap-4
      "
        >
            <span
                className="
          truncate
          font-mono
          text-[11px]
          text-zinc-500
          sm:text-sm
        "
            >
                {item.name}
            </span>

            <div className="h-1 overflow-hidden rounded-full bg-white/5">
                <div
                    className={`h-full rounded-full transition-all duration-1000 ${item.color}`}
                    style={{
                        width: `${item.value}%`,
                    }}
                />
            </div>

            <span
                className="
          text-right
          font-mono
          text-[11px]
          font-bold
          text-zinc-300
          sm:text-sm
        "
            >
                {item.value}%
            </span>
        </div>
    );
}
