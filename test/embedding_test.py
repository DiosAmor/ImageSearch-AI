import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel
import os
from dotenv import load_dotenv
import numpy as np


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


media = "D:/GitHub/ImageSearch-AI/images"
image_path = media + "/test.jpg"
print(image_path)

image = Image.load_from_file(image_path)

load_dotenv()

# 서비스 계정 키 파일 경로 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "D:/GitHub/ImageSearch-AI/vertex-ai-api-key.json"
)

vertexai.init(project=os.getenv("PROJECT_ID"), location="us-central1")
model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")

embeddings = model.get_embeddings(
    image=image,
    contextual_text="snack",
    dimension=1408,
)
embeddings_2 = model.get_embeddings(
    contextual_text="water",
    dimension=1408,
)

print(cosine_similarity(embeddings.image_embedding, embeddings.text_embedding))
print(cosine_similarity(embeddings.image_embedding, embeddings_2.text_embedding))
