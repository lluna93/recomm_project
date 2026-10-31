
import { Button } from "antd";
import styled from "styled-components";

const Header = styled.header`
  height: 64px;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #f0f0f0;

  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Logo = styled.div`
  font-size: 20px;
  font-weight: 700;
  color: #1677ff;
`;

const Actions = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`;

export default function HeaderBar({
                                      user,
                                      onLogin,
                                      onSignup,
                                      onLogout,
                                  }) {
    return (
        <Header>
            <Logo>Recomm Project</Logo>

            <Actions>
                {user ? (
                    <>
                        <span>{user.name || user.email}님</span>

                        <Button onClick={onLogout}>
                            로그아웃
                        </Button>
                    </>
                ) : (
                    <>
                        <Button onClick={onLogin}>
                            로그인
                        </Button>

                        <Button type="primary" onClick={onSignup}>
                            회원가입
                        </Button>
                    </>
                )}
            </Actions>
        </Header>
    );
}
