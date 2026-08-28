import { Check, FileText, Quote, Sparkles } from "lucide-react";
import SectionIntro from "./SectionIntro";
import Reveal from "./Reveal";
import type { ScrollDrive } from "../../Hooks/useScrollDrive";

type Props = {
    drive: ScrollDrive;
};

export default function LearningWorkspace({ drive }: Props) {
    // Page progress re-mapped to the slice this section occupies, so the
    // mock window drifts as it passes and drifts back on the way up.
    const local = Math.min(1, Math.max(0, (drive.progress - 0.18) / 0.34));

    return (
        <section
            id="workspace"
            className="scroll-mt-28 overflow-hidden bg-neutral-950 px-5 py-24 text-white transition-colors sm:px-6 lg:py-32 dark:bg-[#0b0b10]"
        >
            <div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
                <Reveal>
                    <SectionIntro
                        theme="dark"
                        eyebrow="One focused workspace"
                        title="Your resources become a personal learning space."
                        description="Keep the conversation, selected materials, previous sessions, and practice together—without switching between disconnected tools."
                    />
                    <ul className="mt-9 space-y-4">
                        {[
                            "Choose the exact resources a conversation should use",
                            "Continue earlier study sessions without losing context",
                            "Move from an explanation directly into practice",
                            "Review marking feedback beside the original discussion",
                        ].map((item) => (
                            <li
                                key={item}
                                className="flex gap-3 text-sm leading-6 text-neutral-300"
                            >
                                <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-blue-500/15 text-blue-400">
                                    <Check size={12} strokeWidth={3} />
                                </span>
                                {item}
                            </li>
                        ))}
                    </ul>
                </Reveal>

                <div
                    className="relative"
                    style={{
                        transform: `translate3d(0, ${(0.5 - local) * 46}px, 0) rotateX(${(0.5 - local) * 5}deg)`,
                        transformOrigin: "50% 50%",
                    }}
                >
                    <div
                        className="absolute -inset-16 bg-blue-500/10 blur-3xl"
                        style={{ opacity: 0.4 + local * 0.6 }}
                    />
                    <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-[#111116] shadow-2xl">
                        <div className="flex h-12 items-center gap-2 border-b border-white/10 px-5">
                            <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
                            <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                            <span className="ml-3 text-[10px] uppercase tracking-[0.18em] text-white/30">
                                Biology revision
                            </span>
                        </div>
                        <div className="grid min-h-[430px] md:grid-cols-[0.72fr_1.28fr]">
                            <div className="hidden border-r border-white/10 bg-black/20 p-4 md:block">
                                <p className="text-[10px] uppercase tracking-[0.18em] text-white/30">
                                    Selected resources
                                </p>
                                <div className="mt-4 space-y-2">
                                    {[
                                        "Cell biology.pdf",
                                        "Lecture notes.pdf",
                                        "Revision guide.pdf",
                                    ].map((file, index) => (
                                        <div
                                            key={file}
                                            className={`flex items-center gap-2 rounded-xl border p-3 text-xs ${index === 0 ? "border-blue-500/40 bg-blue-500/10 text-white" : "border-white/5 text-white/45"}`}
                                        >
                                            <FileText size={14} />
                                            <span className="truncate">
                                                {file}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                                <p className="mt-8 text-[10px] uppercase tracking-[0.18em] text-white/30">
                                    Recent sessions
                                </p>
                                <div className="mt-3 space-y-3 text-xs text-white/40">
                                    <p>Cell respiration review</p>
                                    <p>Photosynthesis questions</p>
                                    <p>Mock exam practice</p>
                                </div>
                            </div>

                            <div className="flex min-w-0 flex-col">
                                <div className="flex-1 space-y-5 p-5 sm:p-7">
                                    <div className="mr-auto max-w-[90%] rounded-2xl rounded-tl-sm bg-white/5 p-4 text-sm leading-6 text-white/70">
                                        <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-blue-400">
                                            <Sparkles size={13} /> Slashus
                                        </div>
                                        Cellular respiration releases energy
                                        from glucose and stores it as ATP. It
                                        happens through glycolysis, the Krebs
                                        cycle, and oxidative phosphorylation.
                                    </div>
                                    <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-blue-600 p-4 text-sm leading-6">
                                        Compare aerobic and anaerobic
                                        respiration for my exam.
                                    </div>
                                    <div className="mr-auto max-w-[90%] rounded-2xl rounded-tl-sm bg-white/5 p-4 text-sm leading-6 text-white/70">
                                        Aerobic respiration uses oxygen and
                                        produces much more ATP. Anaerobic
                                        respiration works without oxygen but
                                        produces less ATP.
                                        <div className="mt-3 flex gap-2">
                                            <span className="inline-flex items-center gap-1 rounded-full bg-white/5 px-2 py-1 text-[10px] text-white/40">
                                                <Quote size={10} /> p. 42
                                            </span>
                                            <span className="rounded-full bg-white/5 px-2 py-1 text-[10px] text-white/40">
                                                p. 47
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div className="border-t border-white/10 p-4">
                                    <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/30">
                                        Ask a follow-up question…
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
