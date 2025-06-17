import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel
import os
from pathlib import Path
from dotenv import load_dotenv


def get_image_embedding(image_path: str) -> list[float] or None:
    """
    Gemini API의 multimodalembedding@001 모델을 사용해 이미지 임베딩 벡터를 반환합니다.
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
    model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")

    image = Image.load_from_file(image_path)

    embeddings = model.get_embeddings(
        image=image,
        dimension=1408,
    )

    return embeddings.image_embedding if embeddings.image_embedding else None


def get_text_embedding(text: str) -> list[float] or None:
    """
    Gemini API의 multimodalembedding@001 모델을 사용해 텍스트 임베딩 벡터를 반환합니다.
    :param text: 임베딩할 텍스트 (English only)
    :return: 임베딩 벡터(list of float) 또는 None
    """

    # 서비스 계정 키 파일 경로 설정
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
        "D:/GitHub/ImageSearch-AI/vertex-ai-api-key.json"
    )

    vertexai.init(project=os.getenv("PROJECT_ID"), location="us-central1")
    model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")

    embeddings = model.get_embeddings(
        contextual_text=text,
        dimension=1408,
    )

    return embeddings.text_embedding if embeddings.text_embedding else None


if __name__ == "__main__":
    media = "D:/GitHub/ImageSearch-AI/images"
    image_path = media + "/test.jpg"
    print(image_path)

    # embedding = get_image_embedding(image_path)
    embedding = get_text_embedding("배고픔")
    if embedding:
        print(f"Embedding vector: {embedding}")
    else:
        print("Failed to get embedding.")
