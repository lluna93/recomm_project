
import { useState } from "react";
import { Alert, Form, Input, Modal } from "antd";
import { useSignup } from "../query/authQuery";

export default function SignupModal({
                                        open,
                                        onClose,
                                        onSuccess,
                                    }) {
    const [form] = Form.useForm();
    const [error, setError] = useState("");
    const signup = useSignup();

    async function handleSubmit(values) {
        setError("");

        try {
            const data = await signup.mutateAsync({
                name: values.name,
                email: values.email,
                password: values.password,
            });

            onSuccess(values.email, data);
            form.resetFields();
        } catch (err) {
            setError(err.message);
        }
    }

    return (
        <Modal
            title="회원가입"
            open={open}
            onCancel={onClose}
            onOk={() => form.submit()}
            okText="가입하기"
            okButtonProps={{ loading: signup.isPending }}
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
                    label="이름"
                    name="name"
                    rules={[{ required: true, message: "이름을 입력하세요." }]}
                >
                    <Input maxLength={50} />
                </Form.Item>

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
                        { min: 8, message: "8자 이상 입력하세요." },
                    ]}
                >
                    <Input.Password autoComplete="new-password" />
                </Form.Item>

                <Form.Item
                    label="비밀번호 확인"
                    name="confirmPassword"
                    dependencies={["password"]}
                    rules={[
                        { required: true, message: "비밀번호를 확인하세요." },
                        ({ getFieldValue }) => ({
                            validator(_, value) {
                                if (value === getFieldValue("password")) {
                                    return Promise.resolve();
                                }
                                return Promise.reject(
                                    new Error("비밀번호가 일치하지 않습니다.")
                                );
                            },
                        }),
                    ]}
                >
                    <Input.Password autoComplete="new-password" />
                </Form.Item>
            </Form>
        </Modal>
    );
}
