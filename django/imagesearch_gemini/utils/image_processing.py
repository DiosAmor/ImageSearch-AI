import os
import tempfile

import pytz
from geopy.geocoders import Nominatim
from imagesearch_gemini.models import ImageEmbedding
from PIL import Image as PilImage
from PIL.ExifTags import GPSTAGS, TAGS
from timezonefinder import TimezoneFinder

from django.contrib.gis.geos import Point
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .embeddings import get_image_embedding

# ...existing code...


def is_allowed_image_file(filename):
    allowed_ext = [".jpg", ".jpeg", ".png"]
    return any(filename.lower().endswith(ext) for ext in allowed_ext)


# ...existing code...


def process_single_image(image, date_taken_user, user_location, tag_list):
    if not is_allowed_image_file(image.name):
        return "not_allowed"  # 허용되지 않은 확장자
    tmp_path = None
    _, ext = os.path.splitext(image.name)
    if not ext:
        ext = ".jpg"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            for chunk in image.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        gps_point, date_taken_exif, image_unique_id, exif_json = (
            extract_exif_metadata_for_db(tmp_path)
        )
        city_from_gps = None
        if gps_point:
            try:
                geolocator = Nominatim(user_agent="imagesearch")
                location = geolocator.reverse(
                    (gps_point[1], gps_point[0]), language="ko"
                )
                if location and location.raw.get("address"):
                    city_from_gps = (
                        location.raw["address"].get("city")
                        or location.raw["address"].get("town")
                        or location.raw["address"].get("village")
                        or location.raw["address"].get("state")
                    )
            except Exception:
                city_from_gps = None
        if (
            image_unique_id
            and ImageEmbedding.objects.filter(image_unique_id=image_unique_id).exists()
        ):
            return None
        embedding_model, embedding = get_image_embedding(tmp_path)
        point = Point(gps_point[0], gps_point[1]) if gps_point else None
        date_taken_exif_parsed = None
        if date_taken_exif:
            try:
                date_taken_exif_parsed = parse_datetime(
                    date_taken_exif.replace(":", "-", 2).replace(" ", "T")
                )
                if date_taken_exif_parsed is not None and timezone.is_naive(
                    date_taken_exif_parsed
                ):
                    tz = pytz.timezone("Asia/Seoul")
                    if gps_point:
                        tf = TimezoneFinder()
                        tzname = tf.timezone_at(lng=gps_point[0], lat=gps_point[1])
                        if tzname:
                            try:
                                tz = pytz.timezone(tzname)
                            except Exception:
                                pass
                    date_taken_exif_parsed = tz.localize(date_taken_exif_parsed)
            except Exception:
                date_taken_exif_parsed = None
        saved_path = default_storage.save(f"images/{image.name}", image)
        obj = ImageEmbedding.objects.create(
            image_path=saved_path,
            embedding=embedding,
            embedding_model=embedding_model,
            gps=point,
            city_from_gps=city_from_gps,
            date_taken_exif=date_taken_exif_parsed,
            date_taken_user=date_taken_user,
            location_user=user_location,
            image_unique_id=image_unique_id,
            exif_json=exif_json,
        )
        if tag_list:
            obj.tags.add(*tag_list)
        return obj
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# ...existing code...


def exif_to_serializable(obj):
    """EXIF dict/list 내 JSON 직렬화 불가 타입(bytes, IFDRational 등)을 float/int/str/utf-8로 변환"""
    if isinstance(obj, dict):
        return {k: exif_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [exif_to_serializable(v) for v in obj]
    if isinstance(obj, tuple):
        return [exif_to_serializable(v) for v in obj]
    if hasattr(obj, "numerator") and hasattr(obj, "denominator"):
        # IFDRational 등
        try:
            return float(obj)
        except Exception:
            return str(obj)
    elif isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8", errors="replace")
        except Exception:
            return str(obj)
    else:
        return obj


# ...existing code...

EXIF_IGNORE_TAGS = {
    "MakerNote",
    "UserComment",
    "PrintImageMatching",
    "FileSource",
    "SceneType",
    "ComponentsConfiguration",
}

# ...existing code...


def extract_exif_metadata_for_db(image_path):
    """EXIF에서 GPSInfo(위치), DateTimeOriginal(촬영일시), ImageUniqueID는 분리, 나머지는 dict로 묶어 반환
    촬영 일시는 위치가 있다면 기반해서 한국 시간으로 바꿔주는 것이 좋음.
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
                    elif tag_name in EXIF_IGNORE_TAGS:
                        continue
                    elif isinstance(tag_name, int):
                        continue
                    else:
                        exif_dict[tag_name] = exif_to_serializable(value)
    except Exception as e:
        exif_dict["error"] = str(e)
    return gps_point, date_taken, image_unique_id, exif_dict
