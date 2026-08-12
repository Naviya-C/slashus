type Props = {
    eyebrow: string;
    title: string;
    description: string;
    align?: "left" | "center";
    theme?: "light" | "dark";
};

export default function SectionIntro({
    eyebrow,
    title,
    description,
    align = "left",
    theme = "light",
}: Props) {
    return (
        <div
            className={
                align === "center"
                    ? "mx-auto max-w-3xl text-center"
                    : "max-w-2xl"
            }
        >
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-blue-600">
                {eyebrow}
            </p>
            <h2
                className={`mt-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl ${theme === "dark" ? "text-white" : "text-neutral-950"}`}
            >
                {title}
            </h2>
            <p
                className={`mt-5 text-base leading-7 sm:text-lg ${theme === "dark" ? "text-neutral-400" : "text-neutral-600"}`}
            >
                {description}
            </p>
        </div>
    );
}
