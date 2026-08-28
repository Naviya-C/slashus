import type { AuthMeResponse, User } from "./types";

export function normalizeUser(response: AuthMeResponse): User {
    const source = "user" in response ? response.user : response;
    const nameParts = source.name?.trim().split(/\s+/) ?? [];

    return {
        userid: source.userid ?? source.user_id ?? source.id ?? "",
        firstName: source.firstName ?? source.first_name ?? nameParts[0] ?? "",
        lastName:
            source.lastName ??
            source.last_name ??
            nameParts.slice(1).join(" "),
        email: source.email,
        createdAt: source.createdAt ?? source.created_at ?? "",
    };
}
