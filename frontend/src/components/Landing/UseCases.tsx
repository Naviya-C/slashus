import {
    ArrowUpRight,
    BookMarked,
    FileSearch,
    GraduationCap,
} from "lucide-react";
import SectionIntro from "./SectionIntro";
import Reveal from "./Reveal";

const cases = [
    {
        icon: GraduationCap,
        audience: "Before an exam",
        title: "Turn a chapter into a revision partner.",
        text: "Ask for summaries, compare concepts, generate practice questions, and get immediate feedback on your answers.",
        color: "from-blue-600 to-cyan-500",
    },
    {
        icon: FileSearch,
        audience: "During research",
        title: "Make long documents easier to explore.",
        text: "Question multiple papers together, trace useful details back to their pages, and continue the investigation in one session.",
        color: "from-violet-600 to-fuchsia-500",
    },
    {
        icon: BookMarked,
        audience: "While learning",
        title: "Build understanding at your own pace.",
        text: "Ask for a simpler explanation, request an example, or dig deeper without feeling rushed or judged.",
        color: "from-orange-500 to-amber-400",
    },
];

export default function UseCases() {
    return (
        <section
            id="use-cases"
            className="scroll-mt-28 bg-[#f5f5f2] px-5 py-24 transition-colors sm:px-6 lg:py-32 dark:bg-[#0c0c10]"
        >
            <div className="mx-auto max-w-7xl">
                <Reveal>
                <SectionIntro
                    align="center"
                    eyebrow="Made for the moment you need it"
                    title="A better way to work with what you are learning."
                    description="Whether you are revising tonight or exploring a subject over several weeks, Slashus keeps the learning active and focused."
                />
                </Reveal>

                <div className="mt-14 grid gap-5 lg:grid-cols-3">
                    {cases.map(
                        ({ icon: Icon, audience, title, text, color }, index) => (
                            <Reveal key={audience} delay={index * 110} className="h-full">
                            <article
                                className="group flex h-full min-h-[24rem] flex-col overflow-hidden rounded-[2rem] bg-white p-7 shadow-sm transition-transform hover:-translate-y-1 sm:p-8 dark:border dark:border-neutral-800 dark:bg-neutral-900/60"
                            >
                                <div
                                    className={`grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br text-white ${color}`}
                                >
                                    <Icon size={24} />
                                </div>
                                <p className="mt-8 text-xs font-bold uppercase tracking-[0.18em] text-neutral-400 dark:text-neutral-500">
                                    {audience}
                                </p>
                                <h3 className="mt-3 text-2xl font-semibold leading-tight text-neutral-950 dark:text-white">
                                    {title}
                                </h3>
                                <p className="mt-4 text-sm leading-6 text-neutral-600 dark:text-neutral-400">
                                    {text}
                                </p>
                                <div className="mt-auto flex items-center justify-between border-t border-neutral-100 pt-6 text-sm font-semibold text-neutral-950 dark:border-neutral-800 dark:text-white">
                                    A learning flow that adapts
                                    <ArrowUpRight
                                        size={18}
                                        className="transition-transform group-hover:-translate-y-1 group-hover:translate-x-1"
                                    />
                                </div>
                            </article>
                            </Reveal>
                        ),
                    )}
                </div>
            </div>
        </section>
    );
}
