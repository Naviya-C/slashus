/**
 Used to hold access token moduler variable not hold this in local storage,
 Therefore xss can't read it.
 */

let accessToken: string | null = null;

export function getToken(){
    return accessToken;
}

export function setToken(token: string | null){
    accessToken = token;
}