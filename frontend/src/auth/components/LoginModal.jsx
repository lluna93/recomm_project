
import { useState } from "react";
import { Alert, Form, Input, Modal } from "antd";
import { useLogin } from "../query/authQuery";

export default function LoginModal({
                                       open,
                                       onClose,
                                       onSuccess,
                                   }) {
    const [error, setError] = useState("");
    const login = useLogin();
    const [form] = Form.useForm();

    async function handleSubmit(values) {
        setError("");

        try {
            const data = await login.mutateAsync(values);

            if (!data?.access_token) {
                throw new Error("서버에서 토큰을 받지 못했습니다.");
            }

            onSuccess(data.access_token);
            form.resetFields();
            onClose();
        } catch (err) {
            setError(err.message);
        }
    }

    return (
        <Modal
            title="로그인"
            open={open}
            onCancel={onClose}
            onOk={() => form.submit()}
            okText="로그인"
            okButtonProps={{ loading: login.isPending }}
            destroyOnHidden
            afterClose={() => {
                form.resetFields();
                setError("");
            }}
        >
            {error && (
                <Alert
                    type="error"
                    title={error}
                    style={{ marginBottom: 16 }}
                />
            )}

            <Form
                form={form}
                layout="vertical"
                onFinish={handleSubmit}
            >
                <Form.Item
                    label="이메일"
                    name="email"
                    rules={[
                        { required: true, message: "이메일을 입력하세요." },
                        { type: "email", message: "이메일 형식이 아닙니다." },
                    ]}
                >
                    <Input autoComplete="email" />
                </Form.Item>

                <Form.Item
                    label="비밀번호"
                    name="password"
                    rules={[
                        { required: true, message: "비밀번호를 입력하세요." },
                    ]}
                >
                    <Input.Password autoComplete="current-password" />
                </Form.Item>
            </Form>
        </Modal>
    );
}
