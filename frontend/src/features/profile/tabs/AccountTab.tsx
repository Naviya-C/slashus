import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

import * as userApi from "../api";
import { cardClass, fieldClass, primaryButtonClass } from "../styles";
import type { UserProfile } from "../types";

type AccountTabProps = {
    profile: UserProfile;
    onSaved: (profile: UserProfile) => void;
    notify: (message: string) => void;
};

export default function AccountTab({
    profile,
    onSaved,
    notify,
}: AccountTabProps) {
    const [username, setUsername] = useState(profile.username);
    const [busy, setBusy] = useState(false);

    useEffect(() => setUsername(profile.username), [profile.username]);

    const problem =
        username.length > 0 && username.length < 3
            ? "Usernames need at least three characters."
            : /[^a-z0-9_-]/i.test(username)
              ? "Use letters, numbers, hyphens and underscores only."
              : "";

    async function updateUsername() {
        setBusy(true);
        try {
            const saved = await userApi.updateProfile({ username });
            onSaved(saved ?? { ...profile, username });
            notify("Username updated");
        } catch {
            notify("Could not update username");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="space-y-5">
            <section className={`${cardClass} p-5 sm:p-7`}>
                <h2 className="font-semibold text-[var(--tx)]">Username</h2>
                <p className="mt-1 text-sm text-[var(--tx3)]">
                    People find and mention you by this handle.
                </p>
                <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-start">
                    <div className="flex-1">
                        <div className="relative">
                            <span className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm text-[var(--tx3)]">
                                @
                            </span>
                            <input
                                className={`${fieldClass} pl-8`}
                                value={username}
                                onChange={(event) =>
                                    setUsername(event.target.value.trim())
                                }
                            />
                        </div>
                        {problem && (
                            <p className="mt-1.5 text-xs text-red-500">{problem}</p>
                        )}
                    </div>
                    <button
                        type="button"
                        className={primaryButtonClass}
                        disabled={
                            busy ||
                            Boolean(problem) ||
                            username === profile.username ||
                            !username
                        }
                        onClick={updateUsername}
                    >
                        {busy && <Loader2 size={15} className="animate-spin" />}
                        Update
                    </button>
                </div>
            </section>

            <section className={`${cardClass} p-5 sm:p-7`}>
                <h2 className="font-semibold text-[var(--tx)]">Email address</h2>
                <p className="mt-1 text-sm text-[var(--tx3)]">
                    Used to sign in and to receive marking notifications.
                </p>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                    <input
                        className={`${fieldClass} sm:max-w-sm`}
                        value={profile.email}
                        disabled
                    />
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/12 px-2.5 py-1 text-xs font-medium text-emerald-500">
                        <Check size={12} />
                        Verified
                    </span>
                </div>
                <p className="mt-3 text-xs text-[var(--tx3)]">
                    Changing your email requires verification and will be available
                    when the user service is connected.
                </p>
            </section>
        </div>
    );
}
