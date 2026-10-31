import { useEffect, useState } from "react";
import {
    Card,
    Col,
    Row,
    InputNumber,
    Button,
    Table,
    Statistic,
    Tag,
    message,
    Typography,
} from "antd";

import {
    getTransformerKpi,
    getTransformerRecommendations,
} from "../api/transformerApi";

const { Title } = Typography;

export default function TransformerPage() {
    const [userId, setUserId] = useState(1);
    const [kpi, setKpi] = useState(null);
    const [movies, setMovies] = useState([]);

    const [loading, setLoading] = useState(false);
    const [kpiLoading, setKpiLoading] = useState(false);

    // KPI 조회
    useEffect(() => {
        let active = true;

        setKpiLoading(true);

        getTransformerKpi()
            .then((data) => {
                if (active) setKpi(data);
            })
            .catch((err) => {
                if (active) message.error(err.message);
            })
            .finally(() => {
                if (active) setKpiLoading(false);
            });

        return () => {
            active = false;
        };
    }, []);

    // 영화 추천 조회
    const recommend = async () => {
        if (userId == null) {
            message.warning("고객 ID를 입력하세요.");
            return;
        }

        setLoading(true);
        setMovies([]);

        try {
            const data = await getTransformerRecommendations(userId);
            setMovies(data);

            if (data.length === 0) {
                message.info("추천 가능한 영화가 없습니다.");
            }
        } catch (err) {
            message.error(err.message);
        } finally {
            setLoading(false);
        }
    };

    const columns = [
        {
            title: "순위",
            dataIndex: "rank",
            width: 80,
            align: "center",
        },
        {
            title: "영화 ID",
            dataIndex: "movie_id",
            width: 100,
        },
        {
            title: "영화 제목",
            dataIndex: "title",
        },
        {
            title: "장르",
            dataIndex: "genres",
            render: (genres) =>
                (genres || "").split(",").map((genre, index) => (
                    <Tag key={index}>{genre.trim()}</Tag>
                )),
        },
        {
            title: "예측 평점",
            dataIndex: "predicted_rating",
            width: 120,
            align: "center",
            render: (score) => (
                <strong>{Number(score).toFixed(3)}</strong>
            ),
        },
    ];

    return (
        <div style={{ padding: 24 }}>
            <Title level={3}>Transformer 영화 추천</Title>

            {/* 검증 KPI */}
            <Row gutter={[16, 16]}>
                {["mae", "mse", "rmse"].map((key) => (
                    <Col xs={24} sm={8} key={key}>
                        <Card loading={kpiLoading}>
                            <Statistic
                                title={key.toUpperCase()}
                                value={kpi?.[key] ?? 0}
                                precision={4}
                            />
                        </Card>
                    </Col>
                ))}
            </Row>

            {/* 추천 요청 */}
            <Card
                title="고객별 영화 추천 TOP 5"
                style={{ marginTop: 24 }}
            >
                <div
                    style={{
                        display: "flex",
                        gap: 8,
                        marginBottom: 20,
                    }}
                >
                    <InputNumber
                        min={1}
                        value={userId}
                        onChange={setUserId}
                        placeholder="고객 ID"
                        style={{ width: 180 }}
                    />

                    <Button
                        type="primary"
                        loading={loading}
                        onClick={recommend}
                    >
                        추천받기
                    </Button>
                </div>

                <Table
                    rowKey="movie_id"
                    columns={columns}
                    dataSource={movies}
                    loading={loading}
                    pagination={false}
                    locale={{ emptyText: "추천 결과가 없습니다." }}
                />
            </Card>
        </div>
    );
}