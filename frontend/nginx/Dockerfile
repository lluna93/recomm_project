
# 1단계: React/Vite 빌드
FROM node:24-alpine AS build

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build


# 2단계: Nginx 웹서버
FROM nginx:alpine

COPY --from=build \
    /app/dist /usr/share/nginx/html

COPY nginx/nginx.conf \
    /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
