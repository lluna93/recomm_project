import { Menu } from "antd";
import {
    UserOutlined,
    BarChartOutlined,
    ApartmentOutlined,
    RobotOutlined,
} from "@ant-design/icons";

import styled from "styled-components";
import { useNavigate, useLocation } from "react-router-dom";

const Container = styled.aside`
    width: 220px;
    min-height: calc(100vh - 64px);
    background: #ffffff;
    border-right: 1px solid #f0f0f0;
`;

const items = [
    {
        key: "/member",
        icon: <UserOutlined />,
        label: "회원",
    },
    {
        key: "/svd",
        icon: <BarChartOutlined />,
        label: "SVD 추천",
    },
    {
        key: "/mf",
        icon: <ApartmentOutlined />,
        label: "MF 추천",
    },
    {
        key: "/transformer",
        icon: <RobotOutlined />,
        label: "Transformer 추천",
    },
];

export default function SideBar() {
    const navigate = useNavigate();
    const location = useLocation();

    return (
        <Container>
            <Menu
                mode="inline"
                selectedKeys={[location.pathname]}
                items={items}
                onClick={({ key }) => navigate(key)}
            />
        </Container>
    );
}