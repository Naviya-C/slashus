import { Check } from "lucide-react";

export default function ProfileToast({ message }: { message: string }) {
    if (!message) return null;

    return (
        <div
            role="status"
            className="profile-enter fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-xl border border-emerald-500/25 bg-[var(--sf)] px-4 py-2.5 text-sm text-[var(--tx)] shadow-xl shadow-emerald-500/10"
        >
            <Check size={15} className="text-emerald-500" />
            {message}
        </div>
    );
}
