import type { Progress } from "./types";

interface Props {
  item: Progress;
}

export default function ProgressBar({
  item,
}: Props) {
  return (
    <div className="mb-5 grid grid-cols-[90px_1fr_40px] items-center gap-4">
      <span className="font-mono text-sm text-zinc-500">
        {item.name}
      </span>

      <div className="h-1 rounded-full bg-white/5">
        <div
          className={`h-1 rounded-full ${item.color}`}
          style={{
            width: `${item.value}%`,
          }}
        />
      </div>

      <span className="text-right font-mono text-sm font-bold text-zinc-300">
        {item.value}%
      </span>
    </div>
  );
}