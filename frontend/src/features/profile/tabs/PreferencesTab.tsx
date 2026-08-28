import { useState } from "react";

import * as userApi from "../api";
import FormRow from "../components/FormRow";
import PreferenceToggle from "../components/PreferenceToggle";
import { cardClass, fieldClass } from "../styles";
import type { UserPreferences } from "../types";

const DEFAULT_PREFERENCES: UserPreferences = {
    language: "en",
    emailOnMarking: true,
    emailOnShare: true,
    publicProfile: false,
};

export default function PreferencesTab({
    notify,
}: {
    notify: (message: string) => void;
}) {
    const [preferences, setPreferences] =
        useState<UserPreferences>(DEFAULT_PREFERENCES);

    async function update(patch: Partial<UserPreferences>) {
        const previous = preferences;
        const next = { ...previous, ...patch };
        setPreferences(next);

        try {
            await userApi.savePreferences(next);
            notify("Preferences saved");
        } catch {
            setPreferences(previous);
            notify("Could not save preferences");
        }
    }

    return (
        <section className={`${cardClass} p-5 sm:p-7`}>
            <h2 className="font-semibold text-[var(--tx)]">Preferences</h2>
            <div className="mt-5 max-w-md">
                <FormRow label="Interface language">
                    <select
                        className={fieldClass}
                        value={preferences.language}
                        onChange={(event) =>
                            void update({
                                language: event.target
                                    .value as UserPreferences["language"],
                            })
                        }
                    >
                        <option value="en">English</option>
                        <option value="si">සිංහල</option>
                        <option value="ta">தமிழ்</option>
                    </select>
                </FormRow>
            </div>
            <div className="mt-5 grid gap-2.5">
                <PreferenceToggle
                    label="Email me when answers are marked"
                    hint="Written answers are marked by an agent and can take a moment."
                    checked={preferences.emailOnMarking}
                    onChange={(value) => void update({ emailOnMarking: value })}
                />
                <PreferenceToggle
                    label="Email me about sharing"
                    hint="When someone shares a question bucket or requests access."
                    checked={preferences.emailOnShare}
                    onChange={(value) => void update({ emailOnShare: value })}
                />
                <PreferenceToggle
                    label="Discoverable profile"
                    hint="Let other users find you by username when sharing."
                    checked={preferences.publicProfile}
                    onChange={(value) => void update({ publicProfile: value })}
                />
            </div>
        </section>
    );
}
