import {
    ArrowRight,
    BadgeCheck,
    BookOpenText,
    BrainCircuit,
    ChevronDown,
    FileText,
    Play,
    Sparkles,
} from "lucide-react";

import Logo3D from "../Brand/Logo3D";
import { useNav } from "../../Hooks/useNav";
import { useAuth } from "../../context/AuthContext";
import { useCountUp, useInView, useTypewriter } from "../../Hooks/UserScrollRev";
import type { ScrollDrive } from "../../Hooks/useScrollDrive";

type Props = {
    drive: ScrollDrive;
};

const rotating = [
    "question papers.",
    "marking schemes.",
    "practice sets.",
    "instant feedback.",
];

const longest = rotating.reduce((a, b) => (b.length > a.length ? b : a));

const orbitFeatures = [
    { label: "Your PDFs", icon: FileText, position: "left-1/2 top-0 -translate-x-1/2 -translate-y-1/2" },
    { label: "Smart questions", icon: BrainCircuit, position: "right-0 top-1/2 translate-x-1/2 -translate-y-1/2" },
    { label: "Auto marking", icon: BadgeCheck, position: "bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2" },
    { label: "Trusted sources", icon: BookOpenText, position: "left-0 top-1/2 -translate-x-1/2 -translate-y-1/2" },
];

function Hero({ drive }: Props) {
    const { goToLogin, goToChat } = useNav();
    const { user, loading } = useAuth();
    const phrase = useTypewriter(rotating, 55, 28, 1900);

    const [statsRef, statsInView] = useInView(0.35);
    const accuracy = useCountUp(98, 1400, statsInView);
    const sources = useCountUp(3, 900, statsInView);
    const seconds = useCountUp(5, 1100, statsInView);
    const local = Math.min(1, drive.progress * 4);

    return (
        <section className="relative flex min-h-dvh flex-col justify-center overflow-hidden bg-white px-5 pb-16 pt-28 transition-colors sm:px-6 sm:pt-32 dark:bg-neutral-950">
            <div
                className="pointer-events-none absolute inset-0 opacity-[0.45] dark:opacity-[0.22]"
                style={{
                    backgroundImage:
                        "radial-gradient(circle at center, rgba(59,130,246,0.16) 0 1px, transparent 1px)",
                    backgroundSize: "28px 28px",
                    maskImage:
                        "radial-gradient(ellipse 62% 58% at 50% 46%, black 5%, transparent 78%)",
                }}
            />

            <div
                className="pointer-events-none absolute left-1/2 top-[42%] h-[38rem] w-[38rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-400/20 blur-[130px] dark:bg-blue-500/15"
                style={{ transform: `translate3d(-50%, ${local * 55 - 50}%, 0) scale(${1 + local * 0.12})` }}
            />
            <div className="pointer-events-none absolute left-[8%] top-[18%] h-44 w-44 rounded-full bg-cyan-300/20 blur-[80px] dark:bg-cyan-400/10" />
            <div className="pointer-events-none absolute bottom-[10%] right-[6%] h-52 w-52 rounded-full bg-emerald-300/20 blur-[90px] dark:bg-emerald-400/10" />

            <div
                className="relative mx-auto flex w-full max-w-6xl flex-col items-center text-center"
                style={{ opacity: 1 - local * 0.48 }}
            >
                <span className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white/75 px-3.5 py-1.5 text-xs font-semibold tracking-wide text-neutral-600 shadow-sm backdrop-blur-xl dark:border-neutral-800 dark:bg-neutral-900/75 dark:text-neutral-300">
                    <span className="relative grid h-2 w-2 place-items-center">
                        <span className="absolute h-2 w-2 animate-ping rounded-full bg-emerald-500/70" />
                        <span className="h-2 w-2 rounded-full bg-emerald-500" />
                    </span>
                    Sinhala-first · source-grounded AI
                </span>

                <h1 className="mt-5 max-w-5xl text-[clamp(2.35rem,6vw,4.8rem)] font-bold leading-[1.02] tracking-[-0.045em] text-neutral-950 dark:text-white">
                    Turn any document into
                    <span className="grid">
                        <span aria-hidden="true" className="invisible col-start-1 row-start-1">
                            {longest}
                            <span className="ml-0.5 inline-block h-[0.85em] w-[3px] align-middle" />
                        </span>
                        <span className="col-start-1 row-start-1">
                            <span className="bg-gradient-to-r from-blue-600 via-cyan-500 to-emerald-400 bg-clip-text text-transparent">
                                {phrase}
                            </span>
                            <span className="ml-1 inline-block h-[0.82em] w-[3px] translate-y-[0.08em] animate-pulse bg-blue-500 align-middle" />
                        </span>
                    </span>
                </h1>

                <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-600 sm:text-lg sm:leading-8 dark:text-neutral-400">
                    One intelligent learning space around the materials you trust.
                    Generate, review, practise, and improve with evidence from every page.
                </p>

                <div
                    className="relative mt-8 h-[19rem] w-[19rem] sm:h-[24rem] sm:w-[24rem] lg:h-[27rem] lg:w-[27rem]"
                    style={{ transform: `translate3d(0, ${local * 34}px, 0) scale(${1 - local * 0.08})` }}
                >
                    <div className="absolute inset-[9%] rounded-full border border-blue-500/15 bg-white/35 shadow-[0_30px_100px_-40px_rgba(37,99,235,0.55)] backdrop-blur-sm dark:border-blue-400/15 dark:bg-neutral-950/30" />
                    <div className="absolute inset-[18%] rounded-full border border-dashed border-cyan-500/25 dark:border-cyan-300/20" />

                    <div className="absolute inset-[12%] animate-spin rounded-full border border-blue-500/20 [animation-duration:30s] dark:border-blue-400/20">
                        {orbitFeatures.map(({ label, icon: Icon, position }) => (
                            <div key={label} className={`absolute ${position}`}>
                                <div className="animate-spin [animation-direction:reverse] [animation-duration:30s]">
                                    <div className="flex items-center gap-2 whitespace-nowrap rounded-2xl border border-neutral-200/80 bg-white/90 px-3 py-2.5 text-xs font-semibold text-neutral-700 shadow-lg shadow-blue-950/10 backdrop-blur-xl sm:px-4 sm:text-sm dark:border-neutral-700/80 dark:bg-neutral-900/90 dark:text-neutral-200 dark:shadow-black/30">
                                        <span className="grid h-8 w-8 place-items-center rounded-xl bg-blue-500/10 text-blue-500">
                                            <Icon size={16} />
                                        </span>
                                        <span className="hidden min-[390px]:inline">{label}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="absolute inset-[22%]">
                        <Logo3D
                            progress={local}
                            velocity={drive.velocity}
                            size={250}
                            depth={15}
                            spread={0.52}
                        />
                    </div>

                    <span className="absolute left-[18%] top-[21%] h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_16px_4px_rgba(34,211,238,0.35)]" />
                    <span className="absolute bottom-[24%] right-[15%] h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_18px_5px_rgba(52,211,153,0.3)] [animation-delay:700ms]" />
                </div>

                <div className="mt-7 flex w-full flex-col justify-center gap-3 sm:w-auto sm:flex-row">
                    <button
                        onClick={user ? goToChat : goToLogin}
                        disabled={loading}
                        className="group flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-cyan-500 px-7 py-4 font-semibold text-white shadow-lg shadow-blue-600/25 transition hover:scale-[1.03] hover:cursor-pointer disabled:opacity-60"
                    >
                        <Sparkles size={18} />
                        {user ? "Open workspace" : "Try Slashus free"}
                        <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
                    </button>

                    <button className="flex items-center justify-center gap-2 rounded-full border border-neutral-200 bg-white/80 px-7 py-4 font-semibold text-neutral-700 shadow-sm backdrop-blur transition hover:scale-[1.03] hover:bg-white dark:border-neutral-800 dark:bg-neutral-900/80 dark:text-neutral-200 dark:hover:bg-neutral-800">
                        <Play size={18} />
                        See how it works
                    </button>
                </div>

                <div
                    ref={statsRef}
                    className="mt-10 grid w-full max-w-2xl grid-cols-3 gap-3 border-t border-neutral-200/80 pt-6 dark:border-neutral-800"
                >
                    {[
                        { value: `${accuracy}.2%`, label: "Marking accuracy" },
                        { value: `${sources}`, label: "Sources per chat" },
                        { value: `<${seconds}s`, label: "To first answer" },
                    ].map((stat) => (
                        <div key={stat.label}>
                            <p className="text-xl font-bold tabular-nums text-neutral-950 sm:text-2xl dark:text-white">
                                {stat.value}
                            </p>
                            <p className="mt-1 text-[11px] leading-4 text-neutral-500 sm:text-xs">
                                {stat.label}
                            </p>
                        </div>
                    ))}
                </div>
            </div>

            <div
                className="pointer-events-none absolute inset-x-0 bottom-5 hidden justify-center lg:flex"
                style={{ opacity: 1 - local * 1.6 }}
            >
                <span className="flex flex-col items-center gap-1 text-[10px] font-medium uppercase tracking-[0.2em] text-neutral-400 dark:text-neutral-600">
                    Scroll
                    <ChevronDown size={15} className="animate-bounce" />
                </span>
            </div>
        </section>
    );
}

export default Hero;
