import type { User } from "../auth/types";
import type { UserProfile } from "./types";

export function createProfile(user: User | null): UserProfile {
    return {
        userid: user?.userid ?? "",
        username:
            (user?.email ?? "").split("@")[0] ||
            `${user?.firstName ?? ""}${user?.lastName ?? ""}`.toLowerCase(),
        firstName: user?.firstName ?? "",
        lastName: user?.lastName ?? "",
        email: user?.email ?? "",
        avatarUrl: null,
        bio: "",
        location: "",
        website: "",
        institution: "",
        role: "Student",
        createdAt: user?.createdAt ?? "",
    };
}

export function getInitials(profile: UserProfile): string {
    const source =
        `${profile.firstName} ${profile.lastName}`.trim() || profile.email;

    return (
        source
            .split(/[\s@.]+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part[0]?.toUpperCase())
            .join("") || "?"
    );
}

export function getProfileCompletion(profile: UserProfile): number {
    const values = [
        profile.firstName,
        profile.lastName,
        profile.username,
        profile.bio,
        profile.location,
        profile.institution,
        profile.avatarUrl,
    ];

    return Math.round((values.filter(Boolean).length / values.length) * 100);
}
