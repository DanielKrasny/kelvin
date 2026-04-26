export interface ApiClient {
    id: number;
    name: string;
    client_id: string;
    redirect_uri: string | null;
}

export interface UserToken {
    id: number;
    client: ApiClient | null;
    created_at: string | null;
}

export interface CreateUserToken extends UserToken {
    token: string;
}
