import os
from pathlib import Path
from typing import List, Optional, Tuple

import vertexai
from dotenv import load_dotenv
from vertexai.vision_models import Image, MultiModalEmbeddingModel

from .logger import log_api_usage, log_performance

# Gemini API 설정
EMBEDDING_MODEL = "multimodalembedding@001"
VECTOR_DIMENSION = 1408
API_LOCATION = "us-central1"


# 환경 변수 설정
def _setup_google_credentials() -> None:
    """Google Cloud 인증 정보를 설정합니다."""
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv(os.path.join(base_dir, "..", ".env"))

    # 환경 변수에서 인증 파일 경로 가져오기
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS 환경 변수가 설정되지 않았습니다."
        )

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"인증 파일을 찾을 수 없습니다: {credentials_path}")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path


def _initialize_vertex_ai() -> MultiModalEmbeddingModel:
    """Vertex AI를 초기화하고 모델을 반환합니다."""
    project_id = os.getenv("PROJECT_ID")
    if not project_id:
        raise ValueError("PROJECT_ID 환경 변수가 설정되지 않았습니다.")

    vertexai.init(project=project_id, location=API_LOCATION)
    return MultiModalEmbeddingModel.from_pretrained(EMBEDDING_MODEL)


@log_performance
def get_image_embedding(image_path: str) -> Tuple[str, Optional[List[float]]]:
    """Gemini API의 multimodalembedding@001 모델을 사용해 이미지 임베딩 벡터를 생성합니다.

    Args:
        image_path: 임베딩할 이미지 파일 경로

    Returns:
        (embedding_model, embedding_vector) 또는 (embedding_model, None)

    Raises:
        FileNotFoundError: 이미지 파일을 찾을 수 없는 경우
        ValueError: 환경 변수 설정 오류
        Exception: API 호출 실패

    """
    try:
        # 파일 존재 확인
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

        # Google Cloud 인증 설정
        _setup_google_credentials()

        # Vertex AI 초기화
        model = _initialize_vertex_ai()

        # 이미지 로드
        image = Image.load_from_file(image_path)

        # 임베딩 생성
        embeddings = model.get_embeddings(
            image=image,
            dimension=VECTOR_DIMENSION,
        )

        embedding_vector = (
            embeddings.image_embedding if embeddings.image_embedding else None
        )

        if embedding_vector:
            log_api_usage("Gemini Image Embedding", True)
            return EMBEDDING_MODEL, embedding_vector
        log_api_usage("Gemini Image Embedding", False, "No embedding generated")
        return EMBEDDING_MODEL, None

    except Exception as e:
        log_api_usage("Gemini Image Embedding", False, str(e))
        raise


@log_performance
def get_text_embedding(text: str) -> Tuple[str, Optional[List[float]]]:
    """Gemini API의 multimodalembedding@001 모델을 사용해 텍스트 임베딩 벡터를 생성합니다.

    Args:
        text: 임베딩할 텍스트 (영어만 지원)

    Returns:
        (embedding_model, embedding_vector) 또는 (embedding_model, None)

    Raises:
        ValueError: 환경 변수 설정 오류 또는 텍스트 검증 실패
        Exception: API 호출 실패

    """
    try:
        # 텍스트 검증
        if not text or not text.strip():
            raise ValueError("텍스트가 비어있습니다.")

        # Google Cloud 인증 설정
        _setup_google_credentials()

        # Vertex AI 초기화
        model = _initialize_vertex_ai()

        # 임베딩 생성
        embeddings = model.get_embeddings(
            contextual_text=text.strip(),
            dimension=VECTOR_DIMENSION,
        )

        embedding_vector = (
            embeddings.text_embedding if embeddings.text_embedding else None
        )

        if embedding_vector:
            log_api_usage("Gemini Text Embedding", True)
            return EMBEDDING_MODEL, embedding_vector
        log_api_usage("Gemini Text Embedding", False, "No embedding generated")
        return EMBEDDING_MODEL, None

    except Exception as e:
        log_api_usage("Gemini Text Embedding", False, str(e))
        raise


def generate_embedding_vector(image_path: str) -> Optional[List[float]]:
    """이미지 경로로부터 임베딩 벡터를 생성합니다 (Celery 태스크용).

    Args:
        image_path: 이미지 파일 경로

    Returns:
        임베딩 벡터 또는 None

    """
    try:
        _, embedding = get_image_embedding(image_path)
        return embedding
    except Exception:
        # 로깅은 get_image_embedding에서 처리됨
        return None
