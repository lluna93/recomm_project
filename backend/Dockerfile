
FROM python:3.13-slim

WORKDIR /app

# 시스템 패키지
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .

# PyTorch CPU 버전 설치
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# 나머지 Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI 코드
COPY app ./app

# 기존 학습 모델은 Compose 볼륨으로 연결
RUN mkdir -p /app/checkpoint

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]
