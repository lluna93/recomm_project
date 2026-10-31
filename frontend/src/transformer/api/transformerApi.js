const BASE_URL = "/api/transformer";

async function request(url) {
    const response = await fetch(url);

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));

        throw new Error(
            error.detail || `API 오류: ${response.status}`
        );
    }

    return response.json();
}

// 검증 MAE, MSE, RMSE
export function getTransformerKpi() {
    return request(`${BASE_URL}/kpi`);
}

// 고객별 안 본 영화 TOP 5
export function getTransformerRecommendations(userId) {
    return request(
        `${BASE_URL}/recommendations?user_id=${encodeURIComponent(userId)}`
    );
}