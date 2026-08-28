export type User = {
    userid: string;
    firstName: string;
    lastName: string;
    email: string;
    createdAt: string;
};

export type ApiUser = {
    userid?: string;
    user_id?: string;
    id?: string;
    firstName?: string;
    first_name?: string;
    lastName?: string;
    last_name?: string;
    name?: string;
    email: string;
    createdAt?: string;
    created_at?: string;
};

export type AuthMeResponse = ApiUser | { user: ApiUser };

export type LoginResponse = {
    token: string;
};
