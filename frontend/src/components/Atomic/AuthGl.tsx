import { useEffect, useRef, useState } from "react";
import { FcGoogle } from "react-icons/fc";

import { GOOGLE_CLIENT_ID, loadGoogleScript } from "../../lib/google";
import { useAuth } from "../../context/AuthContext";

type Props = {
    onSuccess?: () => void;
};

const AuthGl = ({ onSuccess }: Props) => {
    const { loginWithGoogle } = useAuth();

    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const configured = Boolean(GOOGLE_CLIENT_ID);
    const shownError = configured ? error : "Google sign-in is not configured";

    const handler = useRef<(idToken: string) => void>(() => {});
    const holder = useRef<HTMLDivElement>(null);

    useEffect(() => {
        handler.current = async (idToken: string) => {
            setError(null);
            setBusy(true);
            try {
                await loginWithGoogle(idToken);
                onSuccess?.();
            } catch (e) {
                setError(
                    e instanceof Error ? e.message : "Google sign-in failed",
                );
            } finally {
                setBusy(false);
            }
        };
    }, [loginWithGoogle, onSuccess]);

    useEffect(() => {
        const clientId = GOOGLE_CLIENT_ID;
        if (!clientId) return;

        let cancelled = false;

        loadGoogleScript()
            .then(() => {
                if (cancelled || !holder.current || !window.google) return;

                window.google.accounts.id.initialize({
                    client_id: clientId,
                    callback: (res) => handler.current(res.credential),
                    auto_select: false,
                    cancel_on_tap_outside: true,
                });

                holder.current.innerHTML = "";
                window.google.accounts.id.renderButton(holder.current, {
                    type: "icon",
                    theme: "outline",
                    size: "large",
                    shape: "square",
                });
            })
            .catch(() => {
                if (!cancelled) setError("Could not load Google sign-in");
            });

        return () => {
            cancelled = true;
        };
    }, []);

    return (
        <div className="flex flex-col items-center gap-1">
            <div className="relative w-14 h-14">
                <div
                    aria-hidden="true"
                    className={`
						w-14 h-14
						border border-slate-300 dark:border-neutral-700 rounded-xl
						flex items-center justify-center
						transition
						${busy || !configured ? "opacity-50" : "hover:bg-slate-50 dark:hover:bg-neutral-800"}
					`}
                >
                    <FcGoogle size={28} />
                </div>

                <div
                    ref={holder}
                    className="absolute inset-0 flex items-center justify-center opacity-0"
                    style={{ transform: "scale(1.4)", cursor: "pointer" }}
                />
            </div>

            {shownError && (
                <p
                    role="alert"
                    className="text-xs text-red-600 dark:text-red-400 text-center max-w-[10rem]"
                >
                    {shownError}
                </p>
            )}
        </div>
    );
};

export default AuthGl;
