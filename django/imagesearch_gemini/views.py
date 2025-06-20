import re
from datetime import datetime

from django.shortcuts import render
from imagesearch_gemini.image_processing import process_single_image

from .models import ImageEmbedding, SearchQuery
from .storage.google_drive import list_images_in_google_drive
from .storage.onedrive import list_images_in_onedrive
from .utils import get_text_embedding


def image_upload(request):
    context = {}
    if request.method == "POST":
        upload_type = request.POST.get("upload_type", "single")
        user_date_taken = request.POST.get("date_taken")
        user_location = request.POST.get("location")
        user_tags = request.POST.get("tags")
        tag_list = (
            [t.strip() for t in user_tags.split(",") if t.strip()] if user_tags else []
        )
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
                    context = {"message": "이미지 및 정보 저장 완료"}
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


def cloud_image_list(request):
    """클라우드 드라이브(Google/OneDrive)에서 이미지 목록을 가져와서 사용자에게 보여주는 뷰
    인증이 필요하면 인증 URL을 안내한다.
    선택한 이미지를 임베딩 요청할 수 있다.
    """
    context = {}
    if request.method == "POST":
        cloud = request.POST.get("cloud")  # 'google' or 'onedrive'
        user_email = request.POST.get("cloud_email")
        action = request.POST.get("action")
        selected_images = request.POST.getlist("selected_images")
        try:
            if cloud == "google":
                images = list_images_in_google_drive(user_email)
                context["images"] = images
            elif cloud == "onedrive":
                images = list_images_in_onedrive(user_email)
                context["images"] = images
            else:
                context["message"] = "클라우드 종류를 선택하세요."
            # 선택한 이미지 임베딩 요청 처리
            if action == "embed" and selected_images:
                # 실제 임베딩 로직은 별도 구현 필요 (예: celery task, 즉시 다운로드 후 임베딩 등)
                context["message"] = (
                    f"{len(selected_images)}개의 이미지를 임베딩합니다. (구현 필요)"
                )
                context["selected_images"] = selected_images
        except Exception as e:
            context["message"] = str(e)
        context["cloud"] = cloud
        context["cloud_email"] = user_email
    return render(request, "imagesearch_gemini/cloud_image_list.html", context)
