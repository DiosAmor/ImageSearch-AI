### 프로젝트 개요

이 프로젝트는 사용자가 자연어로 이미지를 검색할 수 있는 기능을 제공합니다. 주요 기능은 다음과 같습니다:

- 사용자가 입력한 자연어 쿼리를 벡터로 변환하여, 유사한 이미지를 검색
- Google Gemini API를 활용해 임베딩 벡터를 생성하고, 벡터 데이터베이스 구축
  - multimodalembedding@001 모델 사용하여, 이미지를 직접 임베딩.
  - 만약, 적절하게 쿼리 되지 않는다면, 캡션을 만들고 임베딩 하는 것으로 수정 예정.
- 이미지 업로드 시 메타데이터(촬영 날짜, 장소 등) 입력 및 저장
- 이미지의 EXIF 정보를 추출해 메타데이터로 활용

### 지원 기능

- 이미지 업로드 및 메타데이터 입력
  - 폴더(여러 장의 이미지) 업로드 및 단일 이미지 업로드 지원
    - 이미지 업로드 제한 기능 추가 필요
  - 구글 드라이브 연동 지원 (예정)
  -
- EXIF 정보 자동 추출
- 자연어 쿼리 기반 이미지 검색
- 검색 결과 시각화
- 자동 태그 기능 (추가 예정)

### 개발 환경

- **언어:** Python 3.11
- **필수 라이브러리:** `requirements.txt` 참고
  - 주요 라이브러리: django, psycopg2-binary, google-genai, google-cloud-aiplatform, python-dotenv, pytz, gunicorn, whitenoise
- **웹 프레임워크:** Django
- **데이터베이스:** PostgreSQL 17 + pgvector + PostGIS 확장
  - 벡터 데이터와 메타데이터(지리데이터,...)를 함께 저장
  - IVFFlat 인덱스를 사용해 벡터 검색 최적화 (인덱스는 직접 생성)
- **컨테이너:** Docker로 Django와 PostgreSQL 컨테이너화

### 주요 기술

- **Gemini API**
  - multimodalembedding@001 모델로 이미지 벡터 생성
  - 참고: [공식 문서](https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-multimodal-embeddings)

### 개발 순서

1. 프로젝트 환경 설정

   - Python 가상 환경(.venv 등) 생성 및 활성화
   - requirements.txt를 이용해 필요한 라이브러리 일괄 설치
   - Django 프로젝트 생성 및 초기 설정
   - Django 앱 생성 (예: 이미지 업로드, 검색 등)
   - settings.py에서 기본 설정(언어, 타임존, 정적/미디어 파일 경로 등) 적용
   - 필요한 Django 앱 및 미들웨어 추가
   - URL 라우팅 및 기본 뷰/템플릿 구조 생성

2. 데이터베이스 및 벡터 저장소 설계

   - PostgreSQL 17 버전을 사용하며, docker-compose.yaml로 컨테이너 실행
   - .env 파일을 이용해 데이터베이스 환경 변수(계정, 비밀번호, 포트 등) 관리
   - pgvector 확장 설치 및 설정
   - PostGIS 확장 설치 및 설정
   - 이미지, 메타데이터, 벡터 정보를 저장할 테이블 설계

3. 이미지 업로드 및 메타데이터 입력 기능 구현

   - Django에서 이미지 업로드 폼 및 API 구현
   - 폴더(여러 장의 이미지) 업로드와 단일 이미지 업로드 두 가지 방식 제공
   - 사용자가 메타데이터(촬영 날짜, 장소 등) 입력 가능하도록 설계

4. EXIF 정보 추출 기능 개발

   - 업로드된 이미지에서 EXIF 정보 자동 추출 및 메타데이터로 저장

5. Gemini API 연동 및 임베딩 벡터 생성

   - 이미지 및 텍스트 쿼리를 Gemini API의 multimodalembedding@001 모델로 전송하여 임베딩 벡터 생성
   - 생성된 벡터를 데이터베이스에 저장

6. 이미지 검색 기능 구현

   - 사용자의 자연어 쿼리를 벡터로 변환
   - 벡터 유사도 기반으로 이미지 검색 및 결과 반환

7. 프론트엔드 및 결과 시각화

   - 검색 결과를 웹에서 시각적으로 보여주는 UI 구현

8. 테스트 및 배포
   - 전체 기능 테스트
   - Docker를 활용한 배포 환경 구성
