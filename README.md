# Recomm Project

추천 시스템 프로젝트 (React + FastAPI + PostgreSQL + Redis)

## 1. Docker 실행

프로젝트 루트에서 실행합니다.

```powershell
cd D:\bej\recomm_project
docker compose up -d
```

## 2. 백엔드 설치 및 실행

```powershell
cd backend

# 가상환경 최초 생성
python -m venv .venv

# 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# 패키지 설치
pip install -r requirements.txt

# FastAPI 실행
python -m uvicorn app.main:app --reload --port 8000
```

## 3. 프론트엔드 설치 및 실행

새 PowerShell 터미널에서 실행합니다.

```powershell
cd D:\bej\recomm_project\frontend

# 패키지 설치
npm install

# React 실행
npm run dev
```

## 4. 접속 주소

- 프론트엔드: http://localhost:5173
- 백엔드 API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## 5. 종료

```powershell
# 각 개발 서버 종료
Ctrl + C

# Docker 종료 (프로젝트 루트)
docker compose down
```

**참고**
- 최초 실행 전 프로젝트 루트에 `.env` 설정이 필요합니다.
- `pip install`, `npm install`은 최초 설치 또는 패키지 변경 시 실행합니다.
- 이후에는 Docker 실행 → 백엔드 실행 → 프론트엔드 실행 순서로 시작하면 됩니다.
