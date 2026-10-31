import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],

    server: {
        host: "localhost",
        port: 5173,

        proxy: {
            "/api/auth": {
                target: "http://localhost:8000",
                changeOrigin: true,
                rewrite: (path) =>
                    path.replace(/^\/api\/auth(?=\/|$)/, "/auth"),
            },

            "/api/users": {
                target: "http://localhost:8000",
                changeOrigin: true,
                rewrite: (path) =>
                    path.replace(/^\/api\/users(?=\/|$)/, "/users"),
            },

            "/api/svd": {
                target: "http://localhost:8000",
                changeOrigin: true,
                rewrite: (path) =>
                    path.replace(/^\/api\/svd(?=\/|$)/, "/svd"),
            },


            "/api/mf": {
                target: "http://localhost:8000",
                changeOrigin: true,
                rewrite: (path) =>
                    path.replace(/^\/api\/mf(?=\/|$)/, "/mf"),
            },

            "/api/transformer": {
                target: "http://localhost:8000",
                changeOrigin: true,
                rewrite: (path) =>
                    path.replace(/^\/api\/transformer(?=\/|$)/, "/transformer"),
            },


            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
        },
    },
});