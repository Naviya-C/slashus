export type UserProfile = {
    userid: string;
    username: string;
    firstName: string;
    lastName: string;
    email: string;
    avatarUrl: string | null;
    bio: string;
    location: string;
    website: string;
    institution: string;
    role: string;
    createdAt: string;
};

export type PasswordChange = {
    currentPassword: string;
    newPassword: string;
};

export type UserPreferences = {
    language: "en" | "si" | "ta";
    emailOnMarking: boolean;
    emailOnShare: boolean;
    publicProfile: boolean;
};

export type LoginSession = {
    id: string;
    device: string;
    location: string;
    lastActive: string;
    current: boolean;
};
