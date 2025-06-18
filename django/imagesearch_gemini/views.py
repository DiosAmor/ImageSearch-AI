from django.shortcuts import render
from .models import ImageEmbedding, SearchQuery
from .utils import get_image_embedding, get_text_embedding, extract_exif_metadata_for_db
from django.core.files.storage import default_storage
from django.contrib.gis.geos import Point
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import tempfile
from datetime import datetime
from timezonefinder import TimezoneFinder
import pytz
import os
import re
from geopy.geocoders import Nominatim
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .google_drive_auth import get_drive_service


def is_allowed_image_file(filename):
    allowed_ext = [".jpg", ".jpeg", ".png"]
    return any(filename.lower().endswith(ext) for ext in allowed_ext)


def process_single_image(image, date_taken_user, user_location, tag_list):
    if not is_allowed_image_file(image.name):
        return "not_allowed"  # 허용되지 않은 확장자
    tmp_path = None
    # 업로드 파일의 확장자 추출 (예: .jpg, .png)
    _, ext = os.path.splitext(image.name)
    if not ext:
        ext = ".jpg"  # 기본값
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            for chunk in image.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        # EXIF 먼저 추출 (임베딩 전에 중복 체크)
        gps_point, date_taken_exif, image_unique_id, exif_json = (
            extract_exif_metadata_for_db(tmp_path)
        )
        # city_from_gps 추출 (geopy)
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
        # image_unique_id 중복 체크
        if (
            image_unique_id
            and ImageEmbedding.objects.filter(image_unique_id=image_unique_id).exists()
        ):
            return None  # 이미 존재하면 임베딩도 하지 않음
        embedding_model, embedding = get_image_embedding(tmp_path)
        point = Point(gps_point[0], gps_point[1]) if gps_point else None
        date_taken_exif_parsed = None
        if date_taken_exif:
            try:
                date_taken_exif_parsed = parse_datetime(
                    date_taken_exif.replace(":", "-", 2).replace(" ", "T")
                )
                # naive datetime이면 타임존 적용
                if date_taken_exif_parsed is not None and timezone.is_naive(
                    date_taken_exif_parsed
                ):
                    # 기본값: 한국 타임존
                    tz = pytz.timezone("Asia/Seoul")
                    # 위경도 정보가 있으면 해당 위치의 타임존 사용
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
            image_path=saved_path,  # 변경: 경로만 저장
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


def image_upload(request):
    context = {}
    if request.method == "POST":
        upload_type = request.POST.get("upload_type", "single")
        # 사용자 입력값
        user_date_taken = request.POST.get("date_taken")
        user_location = request.POST.get("location")
        user_tags = request.POST.get("tags")
        tag_list = (
            [t.strip() for t in user_tags.split(",") if t.strip()] if user_tags else []
        )
        # date_taken_user는 DateField이므로 YYYY-MM-DD로 변환
        date_taken_user = None
        if user_date_taken:
            try:
                date_taken_user = datetime.strptime(user_date_taken, "%Y-%m-%d").date()
            except Exception:
                date_taken_user = None

        if upload_type == "single":
            image = request.FILES.get("image")
            if image:
                obj = process_single_image(
                    image, date_taken_user, user_location, tag_list
                )
                if obj == "not_allowed":
                    context = {"message": "jpg, jpeg, png 파일만 업로드할 수 있습니다."}
                elif obj:
                    context = {"message": f"이미지 및 정보 저장 완료"}
                else:
                    context = {
                        "message": "중복된 이미지(이미 등록된 image_unique_id)로 저장하지 않았습니다."
                    }
            else:
                context = {"message": "파일이 없습니다."}
        elif upload_type == "folder":
            images = request.FILES.getlist("images")
            saved_count = 0
            skipped_count = 0
            not_allowed_count = 0
            for image in images:
                obj = process_single_image(
                    image, date_taken_user, user_location, tag_list
                )
                if obj == "not_allowed":
                    not_allowed_count += 1
                elif obj:
                    saved_count += 1
                else:
                    skipped_count += 1
            context = {
                "message": f"폴더 업로드: {saved_count}개 저장, {skipped_count}개 중복 건너뜀, {not_allowed_count}개 허용되지 않은 확장자 건너뜀"
            }
        else:
            context = {"message": "알 수 없는 업로드 타입"}
        return render(request, "imagesearch_gemini/image_upload.html", context)
    return render(request, "imagesearch_gemini/image_upload.html")


def image_search(request):
    results = None
    message = None
    if request.method == "GET":
        query_text = request.GET.get("query_text")
        tags = request.GET.get("tags")
        location = request.GET.get("location")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        qs = ImageEmbedding.objects.all()
        # 태그 검색
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            for tag in tag_list:
                qs = qs.filter(tags__name__icontains=tag)
        # 장소 검색
        if location:
            qs = qs.filter(location_user__icontains=location)
        # 날짜 검색
        if date_from:
            qs = qs.filter(date_taken_exif__date__gte=date_from)
        if date_to:
            qs = qs.filter(date_taken_exif__date__lte=date_to)
        # 텍스트 임베딩 기반 유사도 검색 (영어만 허용)
        if query_text:
            if not re.fullmatch(r"[A-Za-z0-9 ,]+", query_text):
                message = (
                    "검색어는 영어 단어(알파벳, 숫자, 공백, 쉼표)만 입력 가능합니다."
                )
                results = []
            else:
                # 검색어 임베딩 벡터 캐싱/저장
                sq = SearchQuery.objects.filter(query_text=query_text).first()
                if sq is not None and sq.query_embedding is not None:
                    query_vec = sq.query_embedding
                else:
                    embedding_model, query_vec = get_text_embedding(query_text)
                    sq = SearchQuery.objects.create(
                        query_text=query_text,
                        query_embedding=query_vec,
                        query_embedding_model=embedding_model,
                    )
                if query_vec is not None:
                    vec_str = "[" + ",".join(str(float(x)) for x in query_vec) + "]"
                    qs = qs.extra(
                        select={"l2": f"embedding <-> '{vec_str}'::vector"},
                        order_by=["l2"],
                    )[:20]
        else:
            qs = qs[:50]  # 기본 최대 50개 제한
        if results is None:
            results = qs
    return render(
        request,
        "imagesearch_gemini/image_search.html",
        {"results": results, "message": message, "query_text": query_text},
    )


@csrf_exempt
def google_drive_login(request):
    message = None
    if request.method == "POST":
        try:
            service = get_drive_service()
            # 로그인 성공 시 사용자 이메일 등 정보 확인
            about = service.about().get(fields="user").execute()
            user_email = about.get("user", {}).get("emailAddress", "(이메일 정보 없음)")
            message = f"구글 드라이브 인증 성공! 이메일: {user_email}"
        except Exception as e:
            message = f"구글 드라이브 인증 실패: {e}"
    return render(
        request, "imagesearch_gemini/google_drive_login.html", {"message": message}
    )
