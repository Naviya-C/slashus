import { Sparkles } from "lucide-react";

import { useAuth } from "../../context/AuthContext";

export default function ChatGreeting() {
    const { user } = useAuth();
    const greeting = greetingForHour(new Date().getHours());
    const firstName = user?.firstName?.trim();

    return (
        <>
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-blue-500/20 bg-blue-500/10 shadow-lg shadow-blue-950/20">
                <Sparkles className="text-blue-400" size={23} />
            </div>
            <p className="mt-6 text-sm font-medium text-blue-400">
                {greeting}
                {firstName ? `, ${firstName}` : ""}
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--tx)] sm:text-3xl">
                What would you like to learn today?
            </h1>
        </>
    );
}

function greetingForHour(hour: number) {
    if (hour >= 5 && hour < 12) {
        return "Good morning";
    }

    if (hour >= 12 && hour < 17) {
        return "Good afternoon";
    }

    if (hour >= 17 && hour < 21) {
        return "Good evening";
    }

    return "Good night";
}
