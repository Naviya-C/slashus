import { useEffect, useMemo, useState } from "react";
import { KeyRound, Loader2, LogOut, Monitor } from "lucide-react";

import * as userApi from "../api";
import FormRow from "../components/FormRow";
import {
    cardClass,
    fieldClass,
    ghostButtonClass,
    primaryButtonClass,
} from "../styles";
import type { LoginSession } from "../types";

type SecurityTabProps = {
    notify: (message: string) => void;
    onLogout: () => Promise<void>;
};

function getPasswordStrength(password: string) {
    const score = [
        password.length >= 8,
        /[A-Z]/.test(password),
        /[a-z]/.test(password),
        /\d/.test(password),
        /[^A-Za-z0-9]/.test(password),
    ].filter(Boolean).length;

    return {
        score,
        label:
            ["Very weak", "Weak", "Fair", "Good", "Strong"][
                Math.max(0, score - 1)
            ] ?? "",
        tone:
            score <= 2
                ? "bg-red-500"
                : score === 3
                  ? "bg-amber-500"
                  : "bg-emerald-500",
    };
}

export default function SecurityTab({ notify, onLogout }: SecurityTabProps) {
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmation, setConfirmation] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [sessions, setSessions] = useState<LoginSession[]>([]);

    useEffect(() => {
        let active = true;
        void userApi.fetchSessions().then((rows) => {
            if (active) setSessions(rows);
        });
        return () => {
            active = false;
        };
    }, []);

    const meter = useMemo(
        () => getPasswordStrength(newPassword),
        [newPassword],
    );
    const mismatch = confirmation.length > 0 && confirmation !== newPassword;
    const ready = Boolean(currentPassword && newPassword.length >= 8 && !mismatch);

    async function submit() {
        setBusy(true);
        setError("");
        try {
            await userApi.changePassword({
                currentPassword,
                newPassword,
            });
            setCurrentPassword("");
            setNewPassword("");
            setConfirmation("");
            notify("Password changed");
        } catch (reason) {
            setError(
                reason instanceof Error
                    ? reason.message
                    : "Could not change password",
            );
        } finally {
            setBusy(false);
        }
    }

    async function revokeSession(sessionId: string) {
        try {
            await userApi.revokeSession(sessionId);
            setSessions((current) =>
                current.filter((session) => session.id !== sessionId),
            );
            notify("Session revoked");
        } catch {
            notify("Could not revoke session");
        }
    }

    return (
        <div className="space-y-5">
            <section className={`${cardClass} p-5 sm:p-7`}>
                <h2 className="flex items-center gap-2 font-semibold text-[var(--tx)]">
                    <KeyRound size={17} />
                    Change password
                </h2>
                <div className="mt-5 grid max-w-md gap-4">
                    <FormRow label="Current password">
                        <input
                            type="password"
                            autoComplete="current-password"
                            className={fieldClass}
                            value={currentPassword}
                            onChange={(event) =>
                                setCurrentPassword(event.target.value)
                            }
                        />
                    </FormRow>
                    <FormRow label="New password">
                        <input
                            type="password"
                            autoComplete="new-password"
                            className={fieldClass}
                            value={newPassword}
                            onChange={(event) => setNewPassword(event.target.value)}
                        />
                        {newPassword && (
                            <div className="mt-2 flex items-center gap-2">
                                <div className="h-1 flex-1 overflow-hidden rounded-full bg-[var(--sf3)]">
                                    <div
                                        className={`h-full rounded-full transition-all ${meter.tone}`}
                                        style={{ width: `${(meter.score / 5) * 100}%` }}
                                    />
                                </div>
                                <span className="text-xs text-[var(--tx3)]">
                                    {meter.label}
                                </span>
                            </div>
                        )}
                    </FormRow>
                    <FormRow label="Confirm new password">
                        <input
                            type="password"
                            autoComplete="new-password"
                            className={fieldClass}
                            value={confirmation}
                            onChange={(event) => setConfirmation(event.target.value)}
                        />
                        {mismatch && (
                            <p className="mt-1.5 text-xs text-red-500">
                                Passwords do not match.
                            </p>
                        )}
                    </FormRow>
                    {error && (
                        <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500">
                            {error}
                        </p>
                    )}
                    <button
                        type="button"
                        className={`${primaryButtonClass} w-fit`}
                        disabled={!ready || busy}
                        onClick={submit}
                    >
                        {busy && <Loader2 size={15} className="animate-spin" />}
                        Update password
                    </button>
                </div>
            </section>

            <section className={`${cardClass} p-5 sm:p-7`}>
                <h2 className="flex items-center gap-2 font-semibold text-[var(--tx)]">
                    <Monitor size={17} />
                    Active sessions
                </h2>
                {sessions.length === 0 ? (
                    <p className="mt-4 rounded-xl border border-dashed border-[var(--bd2)] px-4 py-8 text-center text-sm text-[var(--tx3)]">
                        Signed-in devices will be listed here once the user service is
                        connected.
                    </p>
                ) : (
                    <div className="mt-4 space-y-2">
                        {sessions.map((session) => (
                            <div
                                key={session.id}
                                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--bd)] p-3"
                            >
                                <div>
                                    <p className="text-sm text-[var(--tx)]">
                                        {session.device}
                                        {session.current && (
                                            <span className="ml-2 text-xs text-emerald-500">
                                                this device
                                            </span>
                                        )}
                                    </p>
                                    <p className="mt-0.5 text-xs text-[var(--tx3)]">
                                        {session.location} · {session.lastActive}
                                    </p>
                                </div>
                                {!session.current && (
                                    <button
                                        type="button"
                                        className={ghostButtonClass}
                                        onClick={() => revokeSession(session.id)}
                                    >
                                        Revoke
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
                <div className="mt-5 border-t border-[var(--bd)] pt-5">
                    <button
                        type="button"
                        className={ghostButtonClass}
                        onClick={() => void onLogout()}
                    >
                        <LogOut size={15} />
                        Sign out
                    </button>
                </div>
            </section>
        </div>
    );
}
