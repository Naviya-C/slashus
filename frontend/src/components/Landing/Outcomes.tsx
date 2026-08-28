import {
    BookOpenCheck,
    BrainCircuit,
    MessageSquareText,
    Target,
} from "lucide-react";
import SectionIntro from "./SectionIntro";
import Reveal from "./Reveal";

const outcomes = [
    {
        icon: MessageSquareText,
        number: "01",
        title: "Understand difficult material",
        text: "Ask in your own words and receive a clear explanation grounded in the resources you selected.",
        accent: "bg-blue-600",
    },
    {
        icon: BrainCircuit,
        number: "02",
        title: "Practice active recall",
        text: "Turn chapters into focused questions instead of rereading pages and hoping the details stay.",
        accent: "bg-violet-600",
    },
    {
        icon: Target,
        number: "03",
        title: "Find your weak areas",
        text: "Get instant marking and feedback that shows what you understood and what deserves another look.",
        accent: "bg-orange-500",
    },
    {
        icon: BookOpenCheck,
        number: "04",
        title: "Study with confidence",
        text: "Keep answers connected to the source, with page citations that make important details easy to verify.",
        accent: "bg-emerald-600",
    },
];

export default function Outcomes() {
    return (
        <section
            id="benefits"
            className="scroll-mt-28 bg-white px-5 py-24 transition-colors sm:px-6 lg:py-32 dark:bg-neutral-950"
        >
            <div className="mx-auto max-w-7xl">
                <Reveal className="flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
                    <SectionIntro
                        eyebrow="Built for better learning"
                        title="Move from reading to real understanding."
                        description="Slashus helps you to do something useful with every resource: understand it, question it, practise it, and improve from it."
                    />
                </Reveal>

                <div className="mt-14 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {outcomes.map(
                        ({ icon: Icon, number, title, text, accent }, index) => (
                            <Reveal key={title} delay={index * 90} className="h-full">
                            <article
                                className="group h-full rounded-[2rem] border border-neutral-200 bg-neutral-50 p-6 transition-all hover:-translate-y-1 hover:bg-white hover:shadow-xl hover:shadow-neutral-200/60 sm:p-7 dark:border-neutral-800 dark:bg-neutral-900/50 dark:hover:bg-neutral-900 dark:hover:shadow-black/40"
                            >
                                <div className="flex items-center justify-between">
                                    <span
                                        className={`grid h-11 w-11 place-items-center rounded-2xl text-white ${accent}`}
                                    >
                                        <Icon size={20} />
                                    </span>
                                    <span className="text-xs font-semibold tracking-[0.16em] text-neutral-300 dark:text-neutral-700">
                                        {number}
                                    </span>
                                </div>
                                <h3 className="mt-8 text-xl font-semibold text-neutral-950 dark:text-white">
                                    {title}
                                </h3>
                                <p className="mt-3 text-sm leading-6 text-neutral-600 dark:text-neutral-400">
                                    {text}
                                </p>
                            </article>
                            </Reveal>
                        ),
                    )}
                </div>
            </div>
        </section>
    );
}
