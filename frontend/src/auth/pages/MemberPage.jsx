
import { Card, Descriptions, Empty, Spin, Typography } from "antd";
import { useMe } from "../query/authQuery";

const { Title } = Typography;

export default function MemberPage({ isAuthenticated }) {
    const { data: user, isLoading, error } = useMe();

    return (
        <>
            <Title level={3}>회원</Title>

            <Card title="내 정보" style={{ maxWidth: 700 }}>
                {!isAuthenticated ? (
                    <Empty description="로그인 후 회원 정보를 확인할 수 있습니다." />
                ) : isLoading ? (
                    <Spin />
                ) : error ? (
                    <Typography.Text type="danger">
                        {error.message}
                    </Typography.Text>
                ) : (
                    <Descriptions column={1} bordered>
                        <Descriptions.Item label="회원 ID">
                            {user?.id}
                        </Descriptions.Item>

                        <Descriptions.Item label="이름">
                            {user?.name || "-"}
                        </Descriptions.Item>

                        <Descriptions.Item label="이메일">
                            {user?.email}
                        </Descriptions.Item>

                        <Descriptions.Item label="인증 상태">
                            {user?.is_verified ? "인증 완료" : "미인증"}
                        </Descriptions.Item>
                    </Descriptions>
                )}
            </Card>
        </>
    );
}
