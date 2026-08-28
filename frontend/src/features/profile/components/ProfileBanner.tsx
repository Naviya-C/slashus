import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Camera, Loader2, Trash2 } from "lucide-react";

import questionImage from "../../../assets/qGen.png";
import * as userApi from "../api";
import { ghostButtonClass } from "../styles";
import type { UserProfile } from "../types";
import { getInitials } from "../utils";

type ProfileBannerProps = {
    profile: UserProfile;
    onChange: (profile: UserProfile) => void;
    notify: (message: string) => void;
};

const MAX_AVATAR_BYTES = 4 * 1024 * 1024;

export default function ProfileBanner({
    profile,
    onChange,
    notify,
}: ProfileBannerProps) {
    const pickerRef = useRef<HTMLInputElement>(null);
    const [busy, setBusy] = useState(false);
    const [preview, setPreview] = useState<string | null>(null);
    const avatarUrl = preview ?? profile.avatarUrl;

    useEffect(
        () => () => {
            if (preview) URL.revokeObjectURL(preview);
        },
        [preview],
    );

    async function handlePick(event: ChangeEvent<HTMLInputElement>) {
        const file = event.target.files?.[0];
        event.target.value = "";
        if (!file) return;

        if (!file.type.startsWith("image/")) {
            notify("That file is not an image.");
            return;
        }
        if (file.size > MAX_AVATAR_BYTES) {
            notify("Images must be under 4 MB.");
            return;
        }

        const nextPreview = URL.createObjectURL(file);
        setPreview((current) => {
            if (current) URL.revokeObjectURL(current);
            return nextPreview;
        });
        setBusy(true);

        try {
            const uploaded = await userApi.uploadAvatar(file);
            if (uploaded?.url) {
                onChange({ ...profile, avatarUrl: uploaded.url });
                setPreview(null);
            }
            notify("Profile photo updated");
        } catch {
            setPreview(null);
            notify("Could not update profile photo");
        } finally {
            setBusy(false);
        }
    }

    async function handleRemove() {
        try {
            await userApi.removeAvatar();
            setPreview(null);
            onChange({ ...profile, avatarUrl: null });
            notify("Photo removed");
        } catch {
            notify("Could not remove profile photo");
        }
    }

    const displayName =
        `${profile.firstName} ${profile.lastName}`.trim() ||
        profile.username ||
        "Your profile";

    return (
        <section className="relative w-full overflow-hidden border-b border-[var(--bd)] bg-[var(--sf)]">
            <div className="relative h-28 overflow-hidden bg-gradient-to-r from-blue-600 via-cyan-500 to-emerald-400 sm:h-36">
                <div
                    className="absolute inset-0 opacity-25"
                    style={{
                        backgroundImage:
                            "radial-gradient(circle at center, rgba(255,255,255,.75) 0 1px, transparent 1px)",
                        backgroundSize: "24px 24px",
                    }}
                />
                <div className="absolute -left-16 -top-24 h-64 w-64 rounded-full border-[42px] border-white/10" />
                <div className="absolute -bottom-20 right-[22%] h-48 w-48 rounded-full bg-white/10 blur-2xl" />
                <img
                    src={questionImage}
                    alt=""
                    className="profile-float absolute -bottom-16 right-4 w-56 opacity-20 mix-blend-screen sm:right-12 sm:w-72"
                />
            </div>

            <div className="relative flex flex-col gap-4 px-4 pb-5 sm:flex-row sm:items-end sm:justify-between sm:px-7 sm:pb-7 lg:px-9">
                <div className="flex items-end gap-4">
                    <div className="group relative -mt-12 sm:-mt-14">
                        <div className="grid h-24 w-24 place-items-center overflow-hidden rounded-3xl border-4 border-[var(--sf)] bg-gradient-to-br from-blue-600 to-cyan-400 shadow-xl shadow-blue-950/15 sm:h-28 sm:w-28">
                            {avatarUrl ? (
                                <img
                                    src={avatarUrl}
                                    alt={`${displayName}'s profile`}
                                    className="h-full w-full object-cover"
                                />
                            ) : (
                                <span className="text-2xl font-semibold text-white">
                                    {getInitials(profile)}
                                </span>
                            )}
                        </div>
                        <button
                            type="button"
                            onClick={() => pickerRef.current?.click()}
                            aria-label="Change profile photo"
                            disabled={busy}
                            className="absolute -right-1 bottom-1 grid h-9 w-9 place-items-center rounded-xl border-2 border-[var(--sf)] bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-md transition hover:scale-105 disabled:opacity-60"
                        >
                            {busy ? (
                                <Loader2 size={14} className="animate-spin" />
                            ) : (
                                <Camera size={14} />
                            )}
                        </button>
                        <input
                            ref={pickerRef}
                            type="file"
                            accept="image/*"
                            onChange={handlePick}
                            className="hidden"
                        />
                    </div>
                    <div className="pb-1">
                        <h1 className="text-xl font-semibold text-[var(--tx)] sm:text-2xl">
                            {displayName}
                        </h1>
                        <p className="mt-0.5 text-sm text-[var(--tx3)]">
                            @{profile.username || "username"}
                        </p>
                        <span className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-500">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                            {profile.role || "Student"}
                        </span>
                    </div>
                </div>

                {avatarUrl && (
                    <button
                        type="button"
                        className={ghostButtonClass}
                        disabled={busy}
                        onClick={handleRemove}
                    >
                        <Trash2 size={15} />
                        Remove photo
                    </button>
                )}
            </div>
        </section>
    );
}
