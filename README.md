# ImageSearch-AI (이세아)

### 프로젝트 개요

**ImageSearch-AI (이세아)**는 사용자가 자연어로 이미지를 검색할 수 있는 AI 기반 이미지 검색 시스템입니다. Google Gemini API를 활용하여 이미지와 텍스트의 벡터 임베딩을 생성하고, PostgreSQL의 pgvector 확장을 사용하여 고성능 벡터 검색을 제공합니다.

### 주요 기능

#### 🔍 이미지 검색

- **자연어 쿼리 기반 검색**: 사용자가 입력한 자연어를 벡터로 변환하여 유사한 이미지 검색
- **벡터 유사도 검색**: pgvector의 IVFFlat 인덱스를 활용한 고성능 벡터 검색
- **검색 결과 캐싱**: 동일한 검색어에 대한 결과 캐싱으로 응답 속도 향상
- **검색 히스토리**: 사용자의 검색 기록 저장 및 관리

#### 📤 이미지 업로드

- **다양한 업로드 방식**:
  - 로컬 이미지 업로드 (단일/폴더 업로드 지원)
  - Google Drive 연동 (OAuth 인증)
  - OneDrive 연동 (OAuth 인증)
- **비동기 임베딩 처리**: Celery를 활용한 백그라운드 임베딩 생성
- **실시간 상태 모니터링**: 업로드 및 임베딩 진행 상황 실시간 표시
- **파일 검증**: 확장자, 크기, 형식 검증으로 보안 강화

#### 📊 메타데이터 관리

- **EXIF 정보 자동 추출**: 촬영 날짜, GPS 좌표, 카메라 정보 등 자동 추출
- **사용자 메타데이터**: 촬영 날짜, 장소, 설명 등 사용자 입력 정보
- **지리정보 지원**: PostGIS를 활용한 위치 기반 검색 및 시각화

#### 🔐 보안 및 인증

- **OAuth 2.0 인증**: Google Drive, OneDrive 연동을 위한 안전한 인증
- **토큰 관리**: OAuth 토큰의 안전한 저장 및 갱신
- **입력 검증**: 모든 사용자 입력에 대한 철저한 검증
- **환경 변수 관리**: 민감한 정보의 안전한 관리

### 기술 스택

#### 백엔드

- **언어**: Python 3.11
- **웹 프레임워크**: Django 4.2+
- **데이터베이스**: PostgreSQL 17 + pgvector + PostGIS
- **캐시**: Redis (Celery 브로커)
- **비동기 처리**: Celery + Redis
- **AI/ML**: Google Gemini API (multimodalembedding@001)

#### 프론트엔드

- **템플릿 엔진**: Django Templates
- **스타일링**: CSS3
- **JavaScript**: Vanilla JS (AJAX, WebSocket)

#### 인프라

- **컨테이너화**: Docker + Docker Compose
- **웹 서버**: Gunicorn + WhiteNoise
- **로깅**: Django Logging Framework

### 프로젝트 구조

```
ImageSearch-AI/
├── django/                          # Django 프로젝트 루트
│   ├── imagesearch/                 # 프로젝트 설정
│   │   ├── settings.py             # Django 설정
│   │   └── urls.py                 # 메인 URL 설정
│   ├── imagesearch_gemini/         # 메인 이미지 검색 앱
│   │   ├── models.py               # 데이터 모델
│   │   ├── views.py                # 뷰 로직
│   │   ├── tasks.py                # Celery 태스크
│   │   ├── utils/                  # 유틸리티 모듈
│   │   │   ├── embeddings.py       # 임베딩 생성
│   │   │   ├── search.py           # 검색 로직
│   │   │   ├── validators.py       # 입력 검증
│   │   │   └── logger.py           # 로깅 시스템
│   │   ├── tests/                  # 단위 테스트
│   │   │   ├── test_embeddings.py
│   │   │   ├── test_search.py
│   │   │   └── test_validators.py
│   │   └── storage/                # 스토리지 백엔드
│   │       ├── google_drive.py
│   │       ├── onedrive.py
│   │       └── local_drive.py
│   ├── oauth/                      # OAuth 인증 앱
│   │   ├── models.py               # OAuth 토큰 모델
│   │   ├── views.py                # 인증 뷰
│   │   ├── tests/                  # OAuth 테스트
│   │   │   └── test_oauth.py
│   │   └── credentials/            # OAuth 인증 정보
│   └── test/                       # 통합 테스트
│       └── test_full_flow.py
├── docker-compose.yaml             # Docker 구성
├── Dockerfile                      # Docker 이미지
├── requirements.txt                # Python 의존성
└── README.md                       # 프로젝트 문서
```

### 설치 및 실행

#### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-username/ImageSearch-AI.git
cd ImageSearch-AI

# 환경 변수 설정 (현재 .env.example 파일이 없으므로 직접 생성)
# .env 파일을 생성하고 필요한 설정 입력
```

#### 2. Docker를 사용한 실행

```bash
# 컨테이너 빌드 및 실행
docker-compose up -d

# 데이터베이스 마이그레이션
docker-compose exec web python manage.py migrate

# 관리자 계정 생성
docker-compose exec web python manage.py createsuperuser
```

#### 3. 로컬 개발 환경

```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
export $(cat .env | xargs)

# 데이터베이스 마이그레이션
python manage.py migrate

# 개발 서버 실행
python manage.py runserver
```

### 환경 변수 설정

`.env` 파일에 다음 설정이 필요합니다:

```env
# 데이터베이스 설정
POSTGRES_DB=imagesearch
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Google Cloud 설정
GOOGLE_APPLICATION_CREDENTIALS=path/to/vertex-ai-api-key.json
GOOGLE_CLOUD_PROJECT=your-project-id

# OAuth 설정
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
ONEDRIVE_CLIENT_ID=your-onedrive-client-id
ONEDRIVE_CLIENT_SECRET=your-onedrive-client-secret

# Django 설정
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis 설정
REDIS_URL=redis://localhost:6379/0
```

### 테스트 실행

```bash
# 전체 테스트 실행
python manage.py test

# 특정 앱 테스트
python manage.py test imagesearch_gemini
python manage.py test oauth

# 커버리지 테스트
coverage run --source='.' manage.py test
coverage report
coverage html
```

### API 사용법

#### 이미지 업로드

```bash
POST /upload/
Content-Type: multipart/form-data

{
  "image": [파일],
  "title": "이미지 제목",
  "description": "이미지 설명",
  "location": "촬영 장소",
  "date_taken": "2024-01-01"
}
```

#### 이미지 검색

```bash
POST /search/
Content-Type: application/json

{
  "query": "검색할 자연어 쿼리",
  "limit": 20
}
```

#### OAuth 인증

```bash
# Google Drive 연동
GET /oauth/google/login/

# OneDrive 연동
GET /oauth/onedrive/login/
```

### 성능 최적화

#### 벡터 검색 최적화

- **IVFFlat 인덱스**: 고성능 벡터 검색을 위한 인덱스 사용
- **결과 제한**: 기본 20개, 최대 50개 결과로 응답 속도 향상
- **쿼리 캐싱**: 동일한 검색어에 대한 결과 재사용

#### 이미지 처리 최적화

- **비동기 처리**: Celery 워커를 통한 백그라운드 임베딩 생성
- **파일 크기 제한**: 업로드 시 적절한 크기 제한으로 메모리 사용량 최적화
- **중복 방지**: 이미지 고유 ID 기반 중복 업로드 방지

### 보안 고려사항

- **입력 검증**: 모든 사용자 입력에 대한 철저한 검증
- **파일 업로드 보안**: 확장자, 크기, 형식 검증
- **OAuth 토큰 보안**: 안전한 토큰 저장 및 갱신
- **환경 변수 관리**: 민감한 정보의 안전한 관리

### 개발 가이드라인

#### 코드 스타일

- **Python**: PEP 8 준수, Black 포맷터 사용
- **Django**: Django 코딩 스타일 가이드 준수
- **테스트**: 각 기능별 단위 테스트 작성

#### 커밋 메시지 규칙

```
<type>(<scope>): <description>

예시:
feat(upload): add folder upload support
fix(search): resolve embedding generation error
refactor(api): simplify image upload logic
```

### 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

### 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 연락처

프로젝트 관련 문의사항이 있으시면 이슈를 생성해 주세요.

---

**참고**: 이 프로젝트는 Google Gemini API를 사용합니다. API 사용량에 따른 비용이 발생할 수 있습니다.
