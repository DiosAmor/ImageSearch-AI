from django.shortcuts import render


def image_upload(request):
    if request.method == "POST":
        upload_type = request.POST.get("upload_type", "single")
        if upload_type == "single":
            image = request.FILES.get("image")
            # 단일 이미지 업로드 처리 로직 (예: 저장, DB 등록 등)
            context = {
                "message": f"단일 이미지 업로드: {image.name if image else '파일 없음'}"
            }
        elif upload_type == "folder":
            images = request.FILES.getlist("images")
            # 여러 이미지 업로드 처리 로직 (예: 저장, DB 등록 등)
            context = {"message": f"폴더 업로드: {len(images)}개 파일"}
        else:
            context = {"message": "알 수 없는 업로드 타입"}
        return render(request, "imagesearch_gemini/image_upload.html", context)
    return render(request, "imagesearch_gemini/image_upload.html")


def image_search(request):
    # 추후 구현 예정 (검색 폼 및 결과)
    return render(request, "imagesearch_gemini/image_search.html")
