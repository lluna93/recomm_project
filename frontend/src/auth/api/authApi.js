
const API_BASE = "/api";
const TOKEN_KEY = "recomm_access_token";

export const tokenStore = {
    get: () => localStorage.getItem(TOKEN_KEY),

    set: (token) => {
        localStorage.setItem(TOKEN_KEY, token);
    },

    clear: () => {
        localStorage.removeItem(TOKEN_KEY);
    },
};

async function request(path, options = {}) {
    const token = tokenStore.get();

    const headers = {
        "Content-Type": "application/json",
        ...options.headers,
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    let response;

    try {
        response = await fetch(`${API_BASE}${path}`, {
            ...options,
            headers,
        });
    } catch {
        throw new Error("서버에 연결할 수 없습니다.");
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        if (response.status === 401 && token) {
            tokenStore.clear();
            window.dispatchEvent(new Event("auth:expired"));
        }

        const detail = data?.detail ?? data?.message;

        const message =
            typeof detail === "string"
                ? detail
                : Array.isArray(detail)
                    ? detail.map((item) => item.msg).join(", ")
                    : `요청 실패 (${response.status})`;

        throw new Error(message);
    }

    return data;
}

export const authApi = {
    signup: (payload) =>
        request("/users", {
            method: "POST",
            body: JSON.stringify(payload),
        }),

    verifyEmail: (payload) =>
        request("/auth/verify-email", {
            method: "POST",
            body: JSON.stringify(payload),
        }),

    resendCode: (payload) =>
        request("/auth/resend-code", {
            method: "POST",
            body: JSON.stringify(payload),
        }),

    login: (payload) =>
        request("/auth/login", {
            method: "POST",
            body: JSON.stringify(payload),
        }),

    me: () => request("/users/me"),
};
