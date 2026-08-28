import Logo3D from "../Brand/Logo3D";
import type { ScrollDrive } from "../../Hooks/useScrollDrive";

type Props = {
    drive: ScrollDrive;
};

const captions = [
    "Learn smarter.",
    "Practice better.",
    "Improve faster.",
    "Grounded in your own materials.",
];

/**
 * Full-cover panel for the left half of /login and /register.
 * Everything here is driven by `drive.progress`, so the motion runs forward
 * on scroll down and backward on scroll up — on every scroll, both ways.
 */
export default function AuthShowcase({ drive }: Props) {
    const { progress, velocity } = drive;

    // Which caption is showing is a function of scroll position, not a timer.
    const captionIndex = Math.min(
        captions.length - 1,
        Math.floor(progress * captions.length),
    );

    return (
        <div className="relative h-full w-full overflow-hidden bg-[#f2f5fb] transition-colors duration-300 dark:bg-[#05060b]">
            {/* Backdrop wash */}
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_90%_at_75%_15%,rgba(37,99,235,0.16),transparent_60%),radial-gradient(90%_70%_at_20%_85%,rgba(6,182,212,0.14),transparent_62%)] dark:bg-[radial-gradient(120%_90%_at_75%_15%,rgba(37,99,235,0.32),transparent_60%),radial-gradient(90%_70%_at_20%_85%,rgba(6,182,212,0.20),transparent_62%)]" />

            {/* The mark */}
            <Logo3D
                progress={progress}
                velocity={velocity}
                size={440}
                depth={18}
            />

            {/* Wordmark, counter-parallaxed */}
            <div
                className="pointer-events-none absolute inset-x-0 top-0 flex justify-center pt-12 xl:pt-16"
                style={{
                    transform: `translate3d(0, ${-progress * 40}px, 0)`,
                    opacity: 1 - progress * 0.55,
                }}
            >
                <p className="text-[clamp(2rem,4vw,3.2rem)] font-black tracking-[0.28em] text-neutral-900/85 dark:text-white/85">
                    SLASH
                    <span className="text-blue-600 dark:text-blue-400">US</span>
                </p>
            </div>

            {/* Scroll-linked caption */}
            <div
                className="pointer-events-none absolute inset-x-0 bottom-0 px-12 pb-14 xl:px-16 xl:pb-16"
                style={{
                    transform: `translate3d(0, ${progress * 26}px, 0)`,
                }}
            >
                <p className="text-xs font-bold uppercase tracking-[0.32em] text-blue-600 dark:text-blue-400">
                    Sinhala-first learning
                </p>

                <div className="relative mt-4 h-[3.6rem] overflow-hidden">
                    {captions.map((caption, index) => (
                        <p
                            key={caption}
                            className="absolute inset-x-0 top-0 text-2xl font-semibold leading-tight text-neutral-900 transition-all duration-500 xl:text-3xl dark:text-white"
                            style={{
                                opacity: index === captionIndex ? 1 : 0,
                                transform: `translateY(${(index - captionIndex) * 100}%)`,
                            }}
                        >
                            {caption}
                        </p>
                    ))}
                </div>

                {/* Progress rail — makes the up/down scroll legible */}
                <div className="mt-7 h-[3px] w-full overflow-hidden rounded-full bg-neutral-900/10 dark:bg-white/10">
                    <div
                        className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-400"
                        style={{
                            width: `${Math.max(6, progress * 100)}%`,
                            transition: "width 60ms linear",
                        }}
                    />
                </div>
            </div>

            {/* Edge vignette */}
            <div className="pointer-events-none absolute inset-0 shadow-[inset_0_0_140px_40px_rgba(255,255,255,0.55)] dark:shadow-[inset_0_0_160px_50px_rgba(0,0,0,0.65)]" />
        </div>
    );
}
