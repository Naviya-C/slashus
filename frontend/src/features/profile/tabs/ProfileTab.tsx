import { useEffect, useMemo, useState } from "react";
import { Building2, Check, Globe, Loader2, MapPin, Pencil, X } from "lucide-react";

import * as userApi from "../api";
import FormRow from "../components/FormRow";
import {
    cardClass,
    fieldClass,
    ghostButtonClass,
    primaryButtonClass,
} from "../styles";
import type { UserProfile } from "../types";

type ProfileTabProps = {
    profile: UserProfile;
    onSaved: (profile: UserProfile) => void;
    notify: (message: string) => void;
};

export default function ProfileTab({
    profile,
    onSaved,
    notify,
}: ProfileTabProps) {
    const [draft, setDraft] = useState(profile);
    const [editing, setEditing] = useState(false);
    const [busy, setBusy] = useState(false);

    useEffect(() => setDraft(profile), [profile]);

    const dirty = useMemo(
        () => JSON.stringify(draft) !== JSON.stringify(profile),
        [draft, profile],
    );

    function updateField(key: keyof UserProfile, value: string) {
        setDraft((current) => ({ ...current, [key]: value }));
    }

    async function save() {
        setBusy(true);
        try {
            const saved = await userApi.updateProfile(draft);
            onSaved(saved ?? draft);
            setEditing(false);
            notify("Profile saved");
        } catch {
            notify("Could not save profile");
        } finally {
            setBusy(false);
        }
    }

    function cancel() {
        setDraft(profile);
        setEditing(false);
    }

    return (
        <section className={`${cardClass} p-5 sm:p-7`}>
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h2 className="font-semibold text-[var(--tx)]">Public profile</h2>
                    <p className="mt-1 text-sm text-[var(--tx3)]">
                        This is what other people see when you share a question bucket
                        with them.
                    </p>
                </div>
                {!editing && (
                    <button
                        type="button"
                        className={ghostButtonClass}
                        onClick={() => setEditing(true)}
                    >
                        <Pencil size={15} />
                        Edit
                    </button>
                )}
            </div>

            <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <FormRow label="First name">
                    <input
                        className={fieldClass}
                        disabled={!editing}
                        value={draft.firstName}
                        onChange={(event) =>
                            updateField("firstName", event.target.value)
                        }
                    />
                </FormRow>
                <FormRow label="Last name">
                    <input
                        className={fieldClass}
                        disabled={!editing}
                        value={draft.lastName}
                        onChange={(event) =>
                            updateField("lastName", event.target.value)
                        }
                    />
                </FormRow>
                <FormRow label="Institution" icon={Building2}>
                    <input
                        className={fieldClass}
                        disabled={!editing}
                        placeholder="Central College"
                        value={draft.institution}
                        onChange={(event) =>
                            updateField("institution", event.target.value)
                        }
                    />
                </FormRow>
                <FormRow label="Location" icon={MapPin}>
                    <input
                        className={fieldClass}
                        disabled={!editing}
                        placeholder="Badulla, Sri Lanka"
                        value={draft.location}
                        onChange={(event) =>
                            updateField("location", event.target.value)
                        }
                    />
                </FormRow>
                <div className="sm:col-span-2">
                    <FormRow label="Website" icon={Globe}>
                        <input
                            className={fieldClass}
                            disabled={!editing}
                            placeholder="https://"
                            value={draft.website}
                            onChange={(event) =>
                                updateField("website", event.target.value)
                            }
                        />
                    </FormRow>
                </div>
                <div className="sm:col-span-2">
                    <FormRow label="Bio" hint={`${draft.bio.length}/280`}>
                        <textarea
                            rows={3}
                            maxLength={280}
                            disabled={!editing}
                            placeholder="A short line about what you teach or study."
                            value={draft.bio}
                            onChange={(event) => updateField("bio", event.target.value)}
                            className={`${fieldClass} h-auto resize-y py-2.5`}
                        />
                    </FormRow>
                </div>
            </div>

            {editing && (
                <div className="mt-6 flex justify-end gap-2 border-t border-[var(--bd)] pt-5">
                    <button type="button" className={ghostButtonClass} onClick={cancel}>
                        <X size={15} />
                        Cancel
                    </button>
                    <button
                        type="button"
                        className={primaryButtonClass}
                        disabled={!dirty || busy}
                        onClick={save}
                    >
                        {busy ? (
                            <Loader2 size={15} className="animate-spin" />
                        ) : (
                            <Check size={15} />
                        )}
                        Save changes
                    </button>
                </div>
            )}
        </section>
    );
}
