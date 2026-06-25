import type { Feature } from "./types";

interface Props {
  feature: Feature;
}

export default function FeatureItem({
  feature,
}: Props) {
  return (
    <div className="flex gap-5">
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${feature.color}`}
      >
        <span className="text-lg">
          {feature.icon}
        </span>
      </div>

      <div>
        <h3 className="font-mono text-2xl font-bold text-black">
          {feature.title}
        </h3>

        <p className="mt-3 font-mono text-base leading-8 text-[#8c8ca0]">
          {feature.desc}
        </p>
      </div>
    </div>
  );
}