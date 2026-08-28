/**
 * User service client.
 *
 * The user service is not built yet, so every call here is a stub. Each one
 * documents the endpoint it should hit and returns a resolved promise, which
 * keeps the UI fully interactive while the backend is pending. Fill in the
 * bodies and the pages work unchanged — no component touches fetch directly.
 */

import type {
    LoginSession,
    PasswordChange,
    UserProfile,
    UserPreferences,
} from "./types";

/** Wired in later. Until then the UI drives itself from local state. */
const NOT_WIRED = "The user service is not connected yet.";

// GET /api/v1/users/me
export async function fetchProfile(): Promise<UserProfile | null> {
    return null;
}

// PATCH /api/v1/users/me
export async function updateProfile(
    _changes: Partial<UserProfile>,
): Promise<UserProfile | null> {
    void _changes;
    return null;
}

// POST /api/v1/users/me/avatar  (multipart, field name "file")
export async function uploadAvatar(_file: File): Promise<{ url: string } | null> {
    void _file;
    return null;
}

// DELETE /api/v1/users/me/avatar
export async function removeAvatar(): Promise<void> {}

// POST /api/v1/users/me/password
export async function changePassword(_body: PasswordChange): Promise<void> {
    void _body;
    throw new Error(NOT_WIRED);
}

// PUT /api/v1/users/me/preferences
export async function savePreferences(
    _preferences: UserPreferences,
): Promise<void> {
    void _preferences;
}

// GET /api/v1/users/me/sessions
export async function fetchSessions(): Promise<LoginSession[]> {
    return [];
}

// DELETE /api/v1/users/me/sessions/{id}
export async function revokeSession(_id: string): Promise<void> {
    void _id;
}
