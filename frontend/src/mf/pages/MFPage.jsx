import { useEffect, useState } from "react";
import {
    Card, Col, Row, InputNumber,
    Button, Table, message, Statistic
} from "antd";
import {
    getMFKpi,
    getMFRecommendations,
} from "../api/mfApi";

export default function MFPage() {
    const [userId, setUserId] = useState(1);
    const [kpi, setKpi] = useState(null);
    const [movies, setMovies] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        getMFKpi()
            .then(setKpi)
            .catch((err) => message.error(err.message));
    }, []);

    const recommend = async () => {
        if (userId == null) {
            message.warning("고객 ID를 입력하세요.");
            return;
        }

        setLoading(true);

        try {
            const data = await getMFRecommendations(userId);
            setMovies(data);
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
        },
        {
            title: "영화 ID",
            dataIndex: "movie_id",
        },
        {
            title: "영화 제목",
            dataIndex: "title",
        },
        {
            title: "장르",
            dataIndex: "genres",
        },
        {
            title: "예측 평점",
            dataIndex: "predicted_rating",
            render: (v) => Number(v).toFixed(3),
        },
    ];

    return (
        <div style={{ padding: 24 }}>
            <h2>MF 영화 추천</h2>

            <Row gutter={16}>
                {["mae", "mse", "rmse"].map((key) => (
                    <Col span={8} key={key}>
                        <Card>
                            <Statistic
                                title={key.toUpperCase()}
                                value={kpi?.[key]}
                                precision={4}
                            />
                        </Card>
                    </Col>
                ))}
            </Row>

            <Card style={{ marginTop: 24 }}>
                <InputNumber
                    min={1}
                    value={userId}
                    onChange={setUserId}
                    placeholder="고객 ID"
                />

                <Button
                    type="primary"
                    loading={loading}
                    onClick={recommend}
                    style={{ marginLeft: 8 }}
                >
                    추천받기
                </Button>

                <Table
                    style={{ marginTop: 20 }}
                    rowKey="movie_id"
                    columns={columns}
                    dataSource={movies}
                    pagination={false}
                />
            </Card>
        </div>
    );
}