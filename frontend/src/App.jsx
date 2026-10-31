
import { useCallback, useEffect, useState } from "react";
import { message } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import {
    Navigate,
    Route,
    Routes,
    useNavigate,
} from "react-router-dom";

import AppLayout from "./components/AppLayout";

import MemberPage from "./auth/pages/MemberPage";
import LoginModal from "./auth/components/LoginModal";
import SignupModal from "./auth/components/SignupModal";
import VerifyEmailModal from "./auth/components/VerifyEmailModal";

import { tokenStore } from "./auth/api/authApi";
import { useMe } from "./auth/query/authQuery";

import SvdPage from "./svd/pages/SvdPage";
import MFPage from "./mf/pages/MFPage";
import TransformerPage from "./transformer/pages/TransformerPage";

export default function App() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    // 인증 및 모달 상태
    const [modal, setModal] = useState(null);
    const [email, setEmail] = useState("");
    const [verificationData, setVerificationData] = useState(null);

    const [isAuthenticated, setIsAuthenticated] = useState(
        () => Boolean(tokenStore.get())
    );

    // 로그인 사용자 조회
    const { data: user } = useMe();

    // 로그아웃
    const logout = useCallback(() => {
        tokenStore.clear();
        queryClient.clear();

        setIsAuthenticated(false);
        setModal(null);

        navigate("/member");
    }, [queryClient, navigate]);

    // 토큰 만료 이벤트
    useEffect(() => {
        window.addEventListener("auth:expired", logout);

        return () => {
            window.removeEventListener("auth:expired", logout);
        };
    }, [logout]);

    // 로그인 성공
    async function handleLoginSuccess(token) {
        tokenStore.set(token);
        setIsAuthenticated(true);
        setModal(null);

        await queryClient.invalidateQueries({
            queryKey: ["auth", "me"],
        });

        message.success("로그인되었습니다.");
    }

    // 회원가입 성공
    function handleSignupSuccess(registeredEmail, data) {
        setEmail(registeredEmail);
        setVerificationData(data);
        setModal("verify");
    }

    // 이메일 인증 성공
    function handleVerifySuccess() {
        message.success("이메일 인증이 완료되었습니다.");
        setModal("login");
    }

    return (
        <>
            <Routes>
                <Route
                    element={
                        <AppLayout
                            user={isAuthenticated ? user : null}
                            onLogin={() => setModal("login")}
                            onSignup={() => setModal("signup")}
                            onLogout={logout}
                        />
                    }
                >
                    {/* 기본 페이지 */}
                    <Route
                        path="/"
                        element={<Navigate to="/member" replace />}
                    />

                    {/* 회원 페이지 */}
                    <Route
                        path="/member"
                        element={
                            <MemberPage
                                isAuthenticated={isAuthenticated}
                            />
                        }
                    />

                    {/* SVD 추천 */}
                    <Route
                        path="/svd"
                        element={<SvdPage />}
                    />

                    {/* MF 추천 */}
                    <Route
                        path="/mf"
                        element={<MFPage />}
                    />

                    {/* Transformer 추천 - 신규 추가 */}
                    <Route
                        path="/transformer"
                        element={<TransformerPage />}
                    />

                    {/* 잘못된 경로 */}
                    <Route
                        path="*"
                        element={<Navigate to="/member" replace />}
                    />
                </Route>
            </Routes>

            {/* 로그인 */}
            <LoginModal
                open={modal === "login"}
                onClose={() => setModal(null)}
                onSuccess={handleLoginSuccess}
            />

            {/* 회원가입 */}
            <SignupModal
                open={modal === "signup"}
                onClose={() => setModal(null)}
                onSuccess={handleSignupSuccess}
            />

            {/* 이메일 인증 */}
            <VerifyEmailModal
                open={modal === "verify"}
                email={email}
                initialData={verificationData}
                onClose={() => setModal(null)}
                onSuccess={handleVerifySuccess}
            />
        </>
    );
}
