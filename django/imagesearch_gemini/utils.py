import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel
import os
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image as PilImage
from PIL.ExifTags import TAGS, GPSTAGS


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


def extract_exif_metadata_for_db(image_path):
    """
    EXIF에서 GPSInfo(위치), DateTimeOriginal(촬영일시), ImageUniqueID는 분리, 나머지는 dict로 묶어 반환
    :param image_path: 이미지 파일 경로
    :return: (gps_point, date_taken, image_unique_id, exif_json)
    """

    gps_point = None
    date_taken = None
    image_unique_id = None
    exif_dict = {}
    try:
        with PilImage.open(image_path) as img:
            info = img._getexif()
            if info:
                for tag, value in info.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name == "GPSInfo":
                        gps_data = {}
                        for t in value:
                            sub_tag = GPSTAGS.get(t, t)
                            gps_data[sub_tag] = value[t]

                        # 위도/경도 변환
                        def _convert_gps(coord, ref):
                            if isinstance(coord, tuple) and len(coord) == 3:
                                d, m, s = coord
                                val = float(d) + float(m) / 60 + float(s) / 3600
                                if ref in ["S", "W"]:
                                    val = -val
                                return val
                            return None

                        lat = lon = None
                        if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
                            lat = _convert_gps(
                                gps_data["GPSLatitude"], gps_data["GPSLatitudeRef"]
                            )
                        if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
                            lon = _convert_gps(
                                gps_data["GPSLongitude"], gps_data["GPSLongitudeRef"]
                            )
                        if lat is not None and lon is not None:
                            gps_point = (lon, lat)  # (경도, 위도) 순서 (PostGIS Point)
                    elif tag_name == "DateTimeOriginal":
                        date_taken = value
                    elif tag_name == "ImageUniqueID":
                        image_unique_id = value
                    else:
                        exif_dict[tag_name] = value
    except Exception as e:
        exif_dict["error"] = str(e)
    return gps_point, date_taken, image_unique_id, exif_dict


if __name__ == "__main__":
    media = "D:/GitHub/ImageSearch-AI/images"
    image_path = media + "/KakaoTalk_20230219_205438231.jpg"
    print(image_path)

    # EXIF 메타데이터 추출 예시
    gps_point, date_taken, image_unique_id, exif_json = extract_exif_metadata_for_db(
        image_path
    )
    print(f"GPS Point: {gps_point}")
    print(f"Date Taken: {date_taken}")
    print(f"Image Unique ID: {image_unique_id}")
    print(f"EXIF Metadata: {exif_json}")

    # # embedding = get_image_embedding(image_path)
    # embedding = get_text_embedding("배고픔")
    # if embedding:
    #     print(f"Embedding vector: {embedding}")
    # else:
    #     print("Failed to get embedding.")
