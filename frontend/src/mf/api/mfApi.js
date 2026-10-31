const BASE_URL = "/api/mf";

async function request(url) {
    const response = await fetch(url);

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "API 요청 실패");
    }

    return response.json();
}

// 검증 평점의 MAE, MSE, RMSE
export const getMFKpi = () => {
    return request(`${BASE_URL}/kpi`);
};

// 고객별 안 본 영화 TOP 5
export const getMFRecommendations = (userId) => {
    return request(
        `${BASE_URL}/recommendations?user_id=${encodeURIComponent(userId)}`
    );
};