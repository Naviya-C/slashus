import { CheckCircle2, Languages, LibraryBig, ShieldCheck } from "lucide-react";

const points = [
    {
        icon: LibraryBig,
        label: "Source-grounded",
        text: "Answers are created around the materials you choose, not an unrelated generic search.",
    },
    {
        icon: CheckCircle2,
        label: "Verifiable",
        text: "Page citations help you return to the original material and confirm important details.",
    },
    {
        icon: Languages,
        label: "Natural questions",
        text: "Ask naturally, follow up, request another explanation, or change the level of detail.",
    },
    {
        icon: ShieldCheck,
        label: "Your workspace",
        text: "Documents, sessions, answers, and practice stay organized around your learning.",
    },
];

export default function TrustSection() {
    return (
        <section
            id="quality"
            className="scroll-mt-28 bg-white px-5 py-24 transition-colors sm:px-6 lg:py-32 dark:bg-neutral-950"
        >
            <div className="mx-auto max-w-7xl overflow-hidden rounded-[2.5rem] bg-blue-600">
                <div className="grid lg:grid-cols-[0.86fr_1.14fr]">
                    <div className="p-8 text-white sm:p-12 lg:p-16">
                        <p className="text-xs font-bold uppercase tracking-[0.22em] text-blue-100">
                            Designed for trust
                        </p>
                        <h2 className="mt-5 text-3xl font-bold tracking-tight sm:text-4xl">
                            AI support without losing connection to the source.
                        </h2>
                        <p className="mt-5 text-base leading-7 text-blue-100">
                            Slashus is designed to help you reason with your
                            material not replace it. You stay in control of the
                            resources and can verify the answer.
                        </p>
                        <div className="mt-10 rounded-3xl border border-white/15 bg-white/10 p-5">
                            <p className="text-4xl font-bold">3</p>
                            <p className="mt-1 text-sm text-blue-100">
                                resources can be focused in one conversation,
                                keeping retrieval useful and precise.
                            </p>
                        </div>
                    </div>

                    <div className="grid gap-px bg-blue-500 lg:grid-cols-2">
                        {points.map(({ icon: Icon, label, text }) => (
                            <article
                                key={label}
                                className="bg-neutral-950 p-8 sm:p-10 dark:bg-[#0b0b10]"
                            >
                                <Icon size={24} className="text-blue-400" />
                                <h3 className="mt-8 text-lg font-semibold text-white">
                                    {label}
                                </h3>
                                <p className="mt-3 text-sm leading-6 text-neutral-400">
                                    {text}
                                </p>
                            </article>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}
