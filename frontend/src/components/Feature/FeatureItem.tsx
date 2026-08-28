import type { Feature } from "./types";

interface Props {
    feature: Feature;
}

export default function FeatureItem({ feature }: Props) {
    return (
        <div className="flex items-start gap-4 md:gap-5">
            <div
                className={`
          flex
          h-10
          w-10
          shrink-0
          items-center
          justify-center
          rounded-xl
          md:h-11
          md:w-11
          ${feature.color}
        `}
            >
                <span className="text-base md:text-lg">{feature.icon}</span>
            </div>

            <div className="min-w-0 flex-1">
                <h3
                    className="
            break-words
            font-mono
            font-bold
            text-black
            dark:text-white
            text-lg
            sm:text-xl
            lg:text-2xl
          "
                >
                    {feature.title}
                </h3>

                <p
                    className="
            mt-2
            font-mono
            text-sm
            leading-7
            text-[#8c8ca0]
            dark:text-neutral-400
            sm:text-base
            md:mt-3
          "
                >
                    {feature.desc}
                </p>
            </div>
        </div>
    );
}
