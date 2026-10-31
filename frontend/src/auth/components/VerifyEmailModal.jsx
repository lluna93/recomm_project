
import { useEffect, useState } from "react";
import { Alert, Button, Input, Modal, Typography } from "antd";
import {
    useVerifyEmail,
    useResendCode,
} from "../query/authQuery";

const { Text } = Typography;

function parseServerTimes(data) {
    const serverTime = Date.parse(data?.server_time);
    const expiresAt = Date.parse(data?.expires_at);
    const resendAt = Date.parse(data?.resend_available_at);

    if (
        !Number.isFinite(serverTime) ||
        !Number.isFinite(expiresAt) ||
        !Number.isFinite(resendAt)
    ) {
        throw new Error("서버 인증 시간 정보가 올바르지 않습니다.");
    }

    return {
        expiresAt,
        resendAt,
        offset: serverTime - Date.now(),
    };
}

function remainingSeconds(target, offset, now) {
    return Math.max(
        0,
        Math.ceil((target - (now + offset)) / 1000)
    );
}

function formatTime(seconds) {
    const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
    const secs = String(seconds % 60).padStart(2, "0");
    return `${minutes}:${secs}`;
}

export default function VerifyEmailModal({
                                             open,
                                             email,
                                             initialData,
                                             onClose,
                                             onSuccess,
                                         }) {
    const [code, setCode] = useState("");
    const [error, setError] = useState("");
    const [times, setTimes] = useState(null);
    const [now, setNow] = useState(Date.now());

    const verify = useVerifyEmail();
    const resend = useResendCode();

    useEffect(() => {
        if (!open || !initialData) return;

        try {
            setTimes(parseServerTimes(initialData));
            setError("");
            setCode("");
        } catch (err) {
            setTimes(null);
            setError(err.message);
        }
    }, [open, initialData]);

    useEffect(() => {
        if (!open) return;

        const timer = setInterval(() => {
            setNow(Date.now());
        }, 1000);

        return () => clearInterval(timer);
    }, [open]);

    const remaining = times
        ? remainingSeconds(times.expiresAt, times.offset, now)
        : 0;

    const resendRemaining = times
        ? remainingSeconds(times.resendAt, times.offset, now)
        : 0;

    const expired = remaining === 0;

    async function handleVerify() {
        if (expired || code.length !== 6) return;

        setError("");

        try {
            await verify.mutateAsync({ email, code });
            onSuccess();
        } catch (err) {
            setError(err.message);
        }
    }

    async function handleResend() {
        setError("");

        try {
            const data = await resend.mutateAsync({ email });
            setTimes(parseServerTimes(data));
            setNow(Date.now());
            setCode("");
        } catch (err) {
            setError(err.message);
        }
    }

    return (
        <Modal
            title="이메일 인증"
            open={open}
            onCancel={onClose}
            footer={null}
            destroyOnHidden
            afterClose={() => {
                setCode("");
                setError("");
                setTimes(null);
            }}
        >
            <p>{email}로 전송한 인증번호를 입력하세요.</p>

            {error && (
                <Alert
                    type="error"
                    title={error}
                    style={{ marginBottom: 16 }}
                />
            )}

            <div style={{ textAlign: "center", margin: "24px 0" }}>
                <Text
                    strong
                    type={expired ? "danger" : undefined}
                    style={{ fontSize: 28 }}
                >
                    {formatTime(remaining)}
                </Text>
            </div>

            <Input.OTP
                length={6}
                value={code}
                onChange={setCode}
                disabled={expired || verify.isPending}
                style={{ width: "100%", justifyContent: "center" }}
            />

            {expired && (
                <Alert
                    type="warning"
                    title="인증번호가 만료되었습니다. 다시 보내기를 눌러주세요."
                    style={{ marginTop: 16 }}
                />
            )}

            <Button
                type="primary"
                block
                style={{ marginTop: 20 }}
                disabled={expired || code.length !== 6}
                loading={verify.isPending}
                onClick={handleVerify}
            >
                이메일 인증
            </Button>

            <Button
                type="link"
                block
                style={{ marginTop: 12 }}
                disabled={resendRemaining > 0}
                loading={resend.isPending}
                onClick={handleResend}
            >
                {resendRemaining > 0
                    ? `재전송까지 ${formatTime(resendRemaining)}`
                    : "인증번호 다시 보내기"}
            </Button>
        </Modal>
    );
}
