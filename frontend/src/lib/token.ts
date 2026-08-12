let accessToken: string | null = null;

export function getToken() {
    return accessToken;
}

export function setToken(token: string | null) {
    accessToken = token;
}
