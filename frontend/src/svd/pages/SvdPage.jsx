import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    Alert,
    Button,
    Card,
    Col,
    InputNumber,
    Row,
    Space,
    Statistic,
    Table,
    Tag,
    Typography,
} from "antd";
import styled from "styled-components";

import {
    getSvdKpi,
    getSvdRecommendations,
} from "../api/svdApi";

const { Title, Text } = Typography;

const Container = styled.div`
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
`;

const SearchArea = styled(Card)`
  margin: 24px 0;
`;

const columns = [
    {
        title: "순위",
        dataIndex: "rank",
        width: 80,
    },
    {
        title: "영화 ID",
        dataIndex: "movie_id",
        width: 110,
    },
    {
        title: "영화 제목",
        dataIndex: "title",
    },
    {
        title: "장르",
        dataIndex: "genres",
        render: (genres) => (
            <Space size={[4, 4]} wrap>
                {genres.split(", ").map((genre) => (
                    <Tag key={genre}>{genre}</Tag>
                ))}
            </Space>
        ),
    },
    {
        title: "예측 평점",
        dataIndex: "predicted_rating",
        width: 130,
        render: (rating) => (
            <Text strong style={{ color: "#1677ff" }}>
                {rating.toFixed(2)} / 5
            </Text>
        ),
    },
];

export default function SvdPage() {
    const [userId, setUserId] = useState(1);
    const [selectedUserId, setSelectedUserId] = useState(null);

    const kpiQuery = useQuery({
        queryKey: ["svd", "kpi"],
        queryFn: getSvdKpi,
        retry: false,
    });

    const recommendationQuery = useQuery({
        queryKey: ["svd", "recommendations", selectedUserId],
        queryFn: () => getSvdRecommendations(selectedUserId),
        enabled: selectedUserId !== null,
        retry: false,
    });

    const kpi = kpiQuery.data;
    const recommendations =
        recommendationQuery.data?.recommendations ?? [];

    return (
        <Container>
            <Title level={2}>SVD 영화 추천</Title>

            <Text type="secondary">
                희소 행렬 기반 SVD 평점 예측 및 개인화 추천
            </Text>

            {kpiQuery.isError && (
                <Alert
                    type="error"
                    showIcon
                    style={{ marginTop: 16 }}
                    message={kpiQuery.error.message}
                />
            )}

            <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
                {[
                    { title: "MAE", value: kpi?.mae },
                    { title: "MSE", value: kpi?.mse },
                    { title: "RMSE", value: kpi?.rmse },
                ].map((item) => (
                    <Col xs={24} sm={8} key={item.title}>
                        <Card loading={kpiQuery.isLoading}>
                            <Statistic
                                title={item.title}
                                value={item.value ?? 0}
                                precision={4}
                            />
                        </Card>
                    </Col>
                ))}
            </Row>

            <SearchArea>
                <Space wrap>
                    <Text strong>사용자 ID</Text>

                    <InputNumber
                        min={1}
                        value={userId}
                        onChange={setUserId}
                        placeholder="사용자 ID"
                    />

                    <Button
                        type="primary"
                        disabled={!Number.isInteger(userId) || userId < 1}
                        loading={recommendationQuery.isFetching}
                        onClick={() => {
                            setSelectedUserId(null);
                            setTimeout(() => setSelectedUserId(userId), 0);
                        }}
                    >
                        영화 추천
                    </Button>
                </Space>
            </SearchArea>

            {recommendationQuery.isError && (
                <Alert
                    type="error"
                    showIcon
                    style={{ marginBottom: 16 }}
                    message={recommendationQuery.error.message}
                />
            )}

            <Card
                title={
                    selectedUserId !== null
                        ? `사용자 ${selectedUserId} 추천 영화 TOP 5`
                        : "추천 영화 TOP 5"
                }
            >
                <Table
                    rowKey="movie_id"
                    columns={columns}
                    dataSource={recommendations}
                    loading={recommendationQuery.isFetching}
                    pagination={false}
                    locale={{
                        emptyText:
                            selectedUserId === null
                                ? "사용자 ID를 입력하고 영화 추천을 눌러주세요."
                                : "추천할 영화가 없습니다.",
                    }}
                />
            </Card>
        </Container>
    );
}