import logging
import urllib.parse

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from imagesearch_gemini.tasks import generate_image_embedding_task

from .models import ImageEmbedding
from .storage.google_drive import (
    list_folders_and_images_in_google_drive,
    save_google_drive_image,
)
from .storage.local_drive import save_uploaded_image
from .storage.onedrive import list_folders_and_images_in_onedrive, save_onedrive_image
from .utils.image_processing import process_image
from .utils.logger import log_performance
from .utils.search import VectorSearchEngine
from .utils.validators import (
    DateValidator,
    TextValidator,
)

logger = logging.getLogger(__name__)


@log_performance
def image_select(request):
    """이미지 선택 및 임베딩 관리 뷰입니다."""
    context = {}

    # 클라우드에서 선택된 이미지 정보 표시
    if request.method == "GET":
        folder_name = request.GET.get("folder_name")
        image_names = request.GET.get("image_names")
        image_urls = request.GET.get("image_urls")

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
        return render(request, "imagesearch_gemini/image_select.html", context)

    if request.method == "POST":
        upload_type = request.POST.get("upload_type", "single")
        user_date_taken = request.POST.get("date_taken")
        user_location = request.POST.get("location")
        user_tags = request.POST.get("tags")

        if upload_type == "cloud":
            image_urls = request.POST.get("image_urls")
            image_names = request.POST.get("image_names")

            if not image_urls:
                context = {"message": "클라우드에서 이미지를 먼저 선택해주세요."}
                return render(request, "imagesearch_gemini/image_select.html", context)

            url_list = image_urls.split(",") if image_urls else []
            name_list = image_names.split(",") if image_names else []

            saved_count = 0
            skipped_count = 0
            not_allowed_count = 0
            download_failed_count = 0

            for i, url in enumerate(url_list):
                try:
                    file_name = (
                        name_list[i] if i < len(name_list) else f"cloud_image_{i}.jpg"
                    )
                    if not any(
                        file_name.lower().endswith(ext)
                        for ext in [".jpg", ".jpeg", ".png"]
                    ):
                        file_name += ".jpg"

                    try:
                        if "drive.google.com" in url:
                            tmp_path = save_google_drive_image(
                                image_url=url,
                                file_name=file_name,
                                date_taken_user=user_date_taken,
                                location_user=user_location,
                                tags=user_tags,
                            )
                        elif "1drv.ms" in url or "onedrive.live.com" in url:
                            tmp_path = save_onedrive_image(
                                image_url=url,
                                file_name=file_name,
                                date_taken_user=user_date_taken,
                                location_user=user_location,
                                tags=user_tags,
                            )
                        else:
                            raise ValidationError("지원하지 않는 클라우드 URL입니다.")

                        obj = process_image(
                            image_path=tmp_path,
                            date_taken_user=user_date_taken,
                            user_location=user_location,
                            tag_list=[
                                t.strip() for t in user_tags.split(",") if t.strip()
                            ]
                            if user_tags
                            else [],
                        )
                        if obj == "not_allowed":
                            not_allowed_count += 1
                        elif obj:
                            generate_image_embedding_task.delay(obj.id)
                            saved_count += 1
                        else:
                            skipped_count += 1
                    except Exception as save_error:
                        download_failed_count += 1
                        context["message"] = str(save_error)
                        logger.error(
                            f"클라우드 이미지 저장 실패: {url}, 오류: {save_error}"
                        )
                except Exception as e:
                    download_failed_count += 1
                    logger.error(f"클라우드 이미지 처리 실패: {url}, 오류: {e}")

            context["message"] = (
                f"클라우드 이미지 처리: {saved_count}개 저장, {skipped_count}개 중복 건너뜀, {not_allowed_count}개 허용되지 않은 확장자 건너뜀, {download_failed_count}개 처리 실패"
            )
            return render(request, "imagesearch_gemini/image_select.html", context)

        files = (
            request.FILES.getlist("images")
            if upload_type == "folder"
            else [request.FILES.get("image")]
        )
        files = [f for f in files if f]  # None 제거

        if upload_type == "single":
            if files:
                try:
                    tmp_path = save_uploaded_image(
                        files[0],
                        date_taken_user=user_date_taken,
                        location_user=user_location,
                        tags=user_tags,
                    )
                    obj = process_image(
                        image_path=tmp_path,
                        date_taken_user=user_date_taken,
                        user_location=user_location,
                        tag_list=[t.strip() for t in user_tags.split(",") if t.strip()]
                        if user_tags
                        else [],
                    )
                    if obj == "not_allowed":
                        context = {
                            "message": "jpg, jpeg, png 파일만 업로드할 수 있습니다."
                        }
                    elif obj:
                        generate_image_embedding_task.delay(obj.id)
                        context = {"message": "이미지 및 정보 저장 완료"}
                    else:
                        context = {
                            "message": "중복된 이미지(이미 등록된 image_unique_id)로 저장하지 않았습니다."
                        }
                except Exception as e:
                    context = {"message": str(e)}
            else:
                context = {"message": "파일이 없습니다."}

        elif upload_type == "folder":
            saved_count = 0
            skipped_count = 0
            not_allowed_count = 0
            for image in files:
                try:
                    tmp_path = save_uploaded_image(
                        image,
                        date_taken_user=user_date_taken,
                        location_user=user_location,
                        tags=user_tags,
                    )
                    obj = process_image(
                        image_path=tmp_path,
                        date_taken_user=user_date_taken,
                        user_location=user_location,
                        tag_list=[t.strip() for t in user_tags.split(",") if t.strip()]
                        if user_tags
                        else [],
                    )
                    if obj == "not_allowed":
                        not_allowed_count += 1
                    elif obj:
                        generate_image_embedding_task.delay(obj.id)
                        saved_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    not_allowed_count += 1
                    context["message"] = str(e)
            context["message"] = (
                f"폴더 업로드: {saved_count}개 저장, {skipped_count}개 중복 건너뜀, {not_allowed_count}개 허용되지 않은 확장자 건너뜀"
            )
        else:
            context = {"message": "알 수 없는 업로드 타입"}

        return render(request, "imagesearch_gemini/image_select.html", context)

    return render(request, "imagesearch_gemini/image_select.html")


@log_performance
def image_search(request):
    """이미지 검색 뷰입니다."""
    if request.method == "GET":
        query_text = request.GET.get("query_text")
        tags = request.GET.get("tags")
        location = request.GET.get("location")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        # 검색어 검증
        if query_text:
            is_valid, error = TextValidator.validate_search_query(query_text)
            if not is_valid:
                return render(
                    request,
                    "imagesearch_gemini/image_search.html",
                    {"results": [], "message": error, "query_text": query_text},
                )

        # 날짜 범위 검증
        if date_from or date_to:
            is_valid, error = DateValidator.validate_date_range(date_from, date_to)
            if not is_valid:
                return render(
                    request,
                    "imagesearch_gemini/image_search.html",
                    {"results": [], "message": error, "query_text": query_text},
                )

        # 벡터 검색 엔진 사용
        results, error = VectorSearchEngine.search_images(
            query_text=query_text,
            tags=tags,
            location=location,
            date_from=date_from,
            date_to=date_to,
        )

        if error:
            return render(
                request,
                "imagesearch_gemini/image_search.html",
                {"results": [], "message": error, "query_text": query_text},
            )

        return render(
            request,
            "imagesearch_gemini/image_search.html",
            {"results": results, "message": None, "query_text": query_text},
        )

    return render(request, "imagesearch_gemini/image_search.html")


@log_performance
def cloud_image_list(request):
    """클라우드 드라이브(Google/OneDrive)에서 폴더와 이미지를 동시에 가져와 폴더, 이미지는 순서로 보여줍니다."""
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

    # 이미지 선택 후 save 버튼 클릭 시 image_select로 이동
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
        return redirect(f"/image-select/?{params}")

    context.update(
        {
            "folders": folders,
            "images": images,
            "folder_name": folder_name,
            "parent_info": parent_info,
            "cloud": cloud,
            "cloud_email": cloud_email,
        }
    )

    return render(request, "imagesearch_gemini/cloud_image_list.html", context)


@log_performance
def embedding_status_list(request):
    """임베딩 상태 목록을 보여주는 뷰입니다."""
    status_filter = request.GET.get("status", "")

    if status_filter:
        images = ImageEmbedding.objects.filter(embedding_status=status_filter).order_by(
            "-created_at"
        )
    else:
        images = ImageEmbedding.objects.all().order_by("-created_at")

    # 페이지네이션
    paginator = Paginator(images, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": ImageEmbedding.EMBEDDING_STATUS_CHOICES,
    }

    return render(request, "imagesearch_gemini/embedding_status_list.html", context)


def retry_failed_embedding(request, image_id):
    """실패한 임베딩을 재시도하는 뷰입니다."""
    try:
        image = ImageEmbedding.objects.get(id=image_id)
        if image.embedding_status == "failed":
            from .tasks import generate_image_embedding

            generate_image_embedding.delay(image_id)
            return JsonResponse(
                {"success": True, "message": "재시도가 시작되었습니다."}
            )
        return JsonResponse(
            {"success": False, "message": "재시도할 수 없는 상태입니다."}
        )
    except ImageEmbedding.DoesNotExist:
        return JsonResponse({"success": False, "message": "이미지를 찾을 수 없습니다."})


def similar_images(request, image_id):
    """특정 이미지와 유사한 이미지들을 찾는 뷰입니다."""
    try:
        similar_images_qs = VectorSearchEngine.get_similar_images(image_id, limit=10)
        context = {
            "base_image_id": image_id,
            "similar_images": similar_images_qs,
        }
        return render(request, "imagesearch_gemini/similar_images.html", context)
    except Exception as e:
        return render(
            request,
            "imagesearch_gemini/similar_images.html",
            {"error": f"유사 이미지 검색 중 오류가 발생했습니다: {e}"},
        )
