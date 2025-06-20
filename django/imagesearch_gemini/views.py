import re
import urllib.parse
from datetime import datetime

from django.shortcuts import redirect, render

from .models import ImageEmbedding, SearchQuery
from .storage.google_drive import list_folders_and_images_in_google_drive
from .storage.onedrive import list_folders_and_images_in_onedrive
from .utils.embeddings import get_text_embedding
from .utils.image_processing import process_single_image


def image_upload(request):
    context = {}
    # 클라우드 업로드 선택 시 cloud_image_list로 리다이렉트
    if request.method == "GET":
        select_mode = request.GET.get("select_mode")
        cloud = request.GET.get("cloud")
        cloud_email = request.GET.get("cloud_email")
        folder_name = request.GET.get("folder_name")
        image_names = request.GET.get("image_names")
        image_urls = request.GET.get("image_urls")
        if (
            select_mode in ["single", "folder"]
            and cloud in ["google", "onedrive"]
            and cloud_email
        ):
            # cloud_image_list로 파라미터 전달
            return redirect(
                f"/cloud-image-list/?cloud={cloud}&cloud_email={cloud_email}&select_mode={select_mode}"
            )
        # 클라우드에서 선택된 폴더/이미지명 표시
        context.update(
            {
                "folder_name": folder_name,
                "image_names": image_names.replace(",", "<br>")
                if image_names
                else None,
                "image_urls": image_urls,
            }
        )
        return render(request, "imagesearch_gemini/image_upload.html", context)
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
    """클라우드 드라이브(Google/OneDrive)에서 폴더와 이미지를 동시에 가져와 폴더, 이미지는 순서로 보여줌."""
    context = {}
    cloud = request.GET.get("cloud") or request.POST.get("cloud")
    cloud_email = request.GET.get("cloud_email") or request.POST.get("cloud_email")
    parent_id = request.GET.get("parent_id") or request.POST.get("parent_id")
    is_shared = request.GET.get("is_shared") or request.POST.get("is_shared")
    drive_id = request.GET.get("drive_id") or request.POST.get("drive_id")
    is_shared = str(is_shared) == "1"  # True/False
    selected_images = request.POST.getlist("selected_images")
    folders, images = [], []
    folder_name = ""
    parent_info = {"parent_id": None, "drive_id": None, "is_shared": is_shared}
    if cloud == "google":
        try:
            folders, images, folder_name, parent_info = (
                list_folders_and_images_in_google_drive(
                    cloud_email, parent_id, is_shared=is_shared, drive_id=drive_id
                )
            )
        except Exception as e:
            context["message"] = str(e)
            parent_info = {"parent_id": None, "drive_id": None, "is_shared": is_shared}
    elif cloud == "onedrive":
        try:
            folders, images, folder_name, parent_info = (
                list_folders_and_images_in_onedrive(
                    cloud_email, parent_id, is_shared=is_shared, drive_id=drive_id
                )
            )
        except Exception as e:
            context["message"] = str(e)
            parent_info = {"parent_id": None, "drive_id": None, "is_shared": is_shared}
    else:
        parent_info = {"parent_id": None, "drive_id": None, "is_shared": is_shared}
    # 이미지 선택 후 save 버튼 클릭 시 image_upload로 이동
    if request.method == "POST" and selected_images:
        img_names = [img["name"] for img in images if img["id"] in selected_images]
        img_urls = [img["url"] for img in images if img["id"] in selected_images]
        params = urllib.parse.urlencode(
            {
                "cloud": cloud,
                "folder_name": folder_name,
                "image_names": ",".join(img_names),
                "image_urls": ",".join(img_urls),
            }
        )
        return redirect(f"/upload/?{params}")
    context.update(
        {
            "cloud": cloud,
            "cloud_email": cloud_email,
            "parent_id": parent_id,
            "is_shared": int(is_shared),
            "drive_id": drive_id,
            "folder_name": folder_name,
            "folders": folders,
            "images": images,
            "parent_info": parent_info,
        }
    )
    return render(request, "imagesearch_gemini/cloud_image_list.html", context)


def embedding_status_list(request):
    images = ImageEmbedding.objects.all().order_by("-id")[:100]
    return render(
        request, "imagesearch_gemini/embedding_status_list.html", {"images": images}
    )
