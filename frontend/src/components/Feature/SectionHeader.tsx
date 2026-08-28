export default function SectionHeader() {
    return (
        <div className="mb-12 md:mb-16">
            <div className="mb-4 md:mb-5 flex items-center gap-3">
                <div className="h-px w-4 bg-emerald-500" />

                <span className="font-mono text-[10px] md:text-xs font-bold uppercase tracking-[0.3em] text-emerald-500">
                    Features
                </span>
            </div>

            <h2
                className="
        max-w-3xl
        font-mono
        font-black
        leading-[1.05]
        text-black
        dark:text-white
        text-3xl
        sm:text-4xl
        md:text-5xl
        lg:text-6xl
      "
            >
                Everything you need
                <br />
                to run better assessments.
            </h2>
        </div>
    );
}
