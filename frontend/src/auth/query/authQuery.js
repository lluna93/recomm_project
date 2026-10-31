
import { useMutation, useQuery } from "@tanstack/react-query";
import { authApi, tokenStore } from "../api/authApi";

export function useSignup() {
    return useMutation({
        mutationFn: authApi.signup,
    });
}

export function useVerifyEmail() {
    return useMutation({
        mutationFn: authApi.verifyEmail,
    });
}

export function useResendCode() {
    return useMutation({
        mutationFn: authApi.resendCode,
    });
}

export function useLogin() {
    return useMutation({
        mutationFn: authApi.login,
    });
}

export function useMe() {
    return useQuery({
        queryKey: ["auth", "me"],
        queryFn: authApi.me,
        enabled: Boolean(tokenStore.get()),
        retry: false,
        staleTime: 60 * 1000,
    });
}
