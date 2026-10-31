const API_BASE = "/api/svd";

async function request(url) {
    const response = await fetch(url);

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "API 요청에 실패했습니다.");
    }

    return response.json();
}

export function getSvdKpi() {
    return request(`${API_BASE}/kpi`);
}

export function getSvdRecommendations(userId) {
    return request(
        `${API_BASE}/recommendations?user_id=${encodeURIComponent(userId)}`
    );
}