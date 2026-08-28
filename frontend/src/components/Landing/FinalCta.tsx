import { ArrowRight, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function FinalCta() {
    const { user } = useAuth();

    return (
        <section className="bg-white px-5 pb-24 transition-colors sm:px-6 lg:pb-32 dark:bg-neutral-950">
            <div className="relative mx-auto max-w-7xl overflow-hidden rounded-[2.5rem] bg-neutral-950 px-7 dark:border dark:border-neutral-800 dark:bg-[#0b0b10] py-16 text-center text-white sm:px-12 sm:py-20">
                <div className="absolute left-1/2 top-0 h-64 w-64 -translate-x-1/2 rounded-full bg-blue-600/30 blur-3xl" />
                <div className="relative">
                    <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/5 text-blue-400">
                        <Sparkles size={21} />
                    </span>
                    <h2 className="mx-auto mt-6 max-w-3xl text-3xl font-bold tracking-tight sm:text-5xl">
                        Give your study materials something useful to do.
                    </h2>
                    <p className="mx-auto mt-5 max-w-xl text-base leading-7 text-neutral-400">
                        Bring one PDF, ask one real question, and start learning
                        from the resources you already trust.
                    </p>
                    <Link
                        to={user ? "/chat" : "/register"}
                        className="mt-9 inline-flex items-center gap-2 rounded-full bg-white px-6 py-3.5 text-sm font-semibold text-neutral-950 transition-transform hover:scale-105"
                    >
                        {user ? "Continue learning" : "Start learning free"}
                        <ArrowRight size={18} />
                    </Link>
                </div>
            </div>
        </section>
    );
}
