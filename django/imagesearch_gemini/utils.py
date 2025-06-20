import os
from pathlib import Path

import vertexai
from dotenv import load_dotenv
from vertexai.vision_models import Image, MultiModalEmbeddingModel

# Gemini API 임베딩 모델 이름
# 현재는 "multimodalembedding@001"이 최신 모델로 가정
embedding_model = "multimodalembedding@001"


def get_image_embedding(image_path: str):
    """Gemini API의 embedding_model을 사용해 이미지 임베딩 벡터를 반환합니다.
    :param image_path: 임베딩할 이미지 파일 경로
    :return: 임베딩 벡터(list of float) 또는 None
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(os.path.join(BASE_DIR, "..", ".env"))

    # 서비스 계정 키 파일 경로 설정
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
        "D:/GitHub/ImageSearch-AI/vertex-ai-api-key.json"
    )

    vertexai.init(project=os.getenv("PROJECT_ID"), location="us-central1")
    model = MultiModalEmbeddingModel.from_pretrained(embedding_model)

    image = Image.load_from_file(image_path)

    embeddings = model.get_embeddings(
        image=image,
        dimension=1408,
    )

    return embedding_model, (
        embeddings.image_embedding if embeddings.image_embedding else None
    )


def get_text_embedding(text: str):
    """Gemini API의 embedding_model을 사용해 텍스트 임베딩 벡터를 반환합니다.
    :param text: 임베딩할 텍스트 (English only)
    :return: 임베딩 벡터(list of float) 또는 None
    """
    # 서비스 계정 키 파일 경로 설정
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
        "D:/GitHub/ImageSearch-AI/vertex-ai-api-key.json"
    )

    vertexai.init(project=os.getenv("PROJECT_ID"), location="us-central1")
    model = MultiModalEmbeddingModel.from_pretrained(embedding_model)

    embeddings = model.get_embeddings(
        contextual_text=text,
        dimension=1408,
    )

    return embedding_model, (
        embeddings.text_embedding if embeddings.text_embedding else None
    )
