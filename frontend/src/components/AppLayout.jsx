
import { Outlet } from "react-router-dom";
import styled from "styled-components";

import HeaderBar from "./HeaderBar";
import SideBar from "./SideBar";

const Body = styled.div`
  display: flex;
  min-height: calc(100vh - 64px);
`;

const Content = styled.main`
  flex: 1;
  padding: 32px;
  background: #f5f7fb;
  min-width: 0;
`;

export default function AppLayout({
                                      user,
                                      onLogin,
                                      onSignup,
                                      onLogout,
                                  }) {
    return (
        <>
            <HeaderBar
                user={user}
                onLogin={onLogin}
                onSignup={onSignup}
                onLogout={onLogout}
            />

            <Body>
                <SideBar />

                <Content>
                    <Outlet />
                </Content>
            </Body>
        </>
    );
}
