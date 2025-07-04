import os
import tempfile
from datetime import datetime

import requests
from imagesearch_gemini.utils.validators import validate_upload_data
from oauth.onedrive import build_onedrive_auth_url
from oauth.utils import get_token

from django.core.exceptions import ValidationError
from django.core.files import File

# 파일 크기 변환을 위한 상수
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024

# HTTP 응답 상태 코드
HTTP_OK = 200


def _parse_onedrive_items(items, is_shared=False):
    """폴더/이미지 분류 및 변환 (공유/내드라이브 공통)"""
    folders = []
    images = []
    for item in items:
        # 공유 항목은 remoteItem, 일반 항목은 item
        base = item.get("remoteItem", item) if is_shared else item
        item_id = base.get("id", "")
        name = base.get("name", "")
        last_modified = base.get("lastModifiedDateTime", "")
        if last_modified:
            date_obj = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
        else:
            formatted_date = ""
        folder_type = "폴더(공유)" if is_shared else "폴더"
        image_type = "(공유)" if is_shared else ""
        drive_id = None
        if is_shared:
            # 공유폴더는 driveId 필요
            parent_ref = base.get("parentReference", {})
            drive_id = parent_ref.get("driveId")
        if base.get("folder", None):
            folders.append(
                {
                    "id": item_id,
                    "name": name + (" (공유됨)" if is_shared else ""),
                    "date": formatted_date,
                    "type": folder_type,
                    "shared": is_shared,
                    "drive_id": drive_id,
                }
            )
        elif _is_image_file(name):
            size_bytes = base.get("size", 0)
            if size_bytes < BYTES_PER_KB:
                size_str = f"{size_bytes} B"
            elif size_bytes < BYTES_PER_MB:
                size_str = f"{size_bytes / BYTES_PER_KB:.1f} KB"
            else:
                size_str = f"{size_bytes / BYTES_PER_MB:.1f} MB"
            _, ext = os.path.splitext(name)
            file_type = ext.upper().replace(".", "") if ext else "이미지"
            images.append(
                {
                    "id": item_id,
                    "name": name + (" (공유됨)" if is_shared else ""),
                    "url": base.get("webUrl", ""),
                    "date": formatted_date,
                    "size": size_str,
                    "type": file_type + image_type,
                    "shared": is_shared,
                }
            )
    return folders, images


def list_folders_and_images_in_onedrive(
    user_email, parent_id=None, is_shared=False, drive_id=None
):
    """OneDrive에서 폴더/이미지 목록을 가져온다. 공유폴더도 일반 폴더처럼 탐색 가능.
    parent_id: 폴더 id (None이면 루트)
    is_shared: 공유폴더 탐색 여부
    drive_id: 공유폴더 탐색 시 driveId
    """
    access_token = get_token(user_email, "onedrive")
    if not access_token:
        auth_url = build_onedrive_auth_url()
        raise Exception(
            f"OneDrive 인증이 필요합니다. <a href='{auth_url}' class='cloud-auth-link' target='_blank'>OneDrive 인증하기</a>"
        )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    # 폴더 이름 및 children API URL 결정
    if is_shared and parent_id and drive_id:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}/children"
        folder_url = (
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}"
        )
        folder_name = "공유 폴더"
    elif parent_id and parent_id != "root":
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}/children"
        folder_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}"
        folder_name = "내 폴더"
    else:
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
        folder_url = "https://graph.microsoft.com/v1.0/me/drive/root"
        folder_name = "내 폴더"
    parent_info = {}
    try:
        folder_response = requests.get(folder_url, headers=headers, timeout=30)
        if folder_response.status_code == HTTP_OK:
            folder_data = folder_response.json()
            folder_name = folder_data.get("name", folder_name)
            parent_ref = folder_data.get("parentReference", {})
            parent_info = {
                "parent_id": parent_ref.get("id"),
                "drive_id": parent_ref.get("driveId"),
                "is_shared": is_shared
                or (
                    parent_ref.get("driveId") is not None
                    and drive_id is not None
                    and parent_ref.get("driveId") != drive_id
                ),
            }
    except Exception:
        pass
    # 항목 목록 가져오기
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != HTTP_OK:
        raise Exception(f"OneDrive 목록 조회 실패: {response.text}")
    items = response.json().get("value", [])
    folders, images = _parse_onedrive_items(items, is_shared=is_shared)
    # 루트에서는 sharedWithMe도 추가
    if not parent_id or parent_id == "root":
        shared_url = "https://graph.microsoft.com/v1.0/me/drive/sharedWithMe"
        shared_response = requests.get(shared_url, headers=headers, timeout=30)
        if shared_response.status_code == HTTP_OK:
            shared_items = shared_response.json().get("value", [])
            shared_folders, shared_images = _parse_onedrive_items(
                shared_items, is_shared=True
            )
            folders.extend(shared_folders)
            images.extend(shared_images)
    return folders, images, folder_name, parent_info


def _is_image_file(filename: str) -> bool:
    """파일명으로 이미지 파일인지 판단"""
    image_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".svg",
        ".tiff",
        ".ico",
    ]
    _, ext = os.path.splitext(filename.lower())
    return ext in image_extensions


def save_onedrive_image(
    image_url: str, file_name: str, date_taken_user=None, location_user=None, tags=None
) -> str:
    """OneDrive 이미지를 다운로드하여 임시로 저장하고, 임시 파일 경로를 반환합니다."""
    response = requests.get(image_url, timeout=30)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if not any(ext in content_type.lower() for ext in ["jpeg", "jpg", "png"]):
        raise ValidationError("지원하지 않는 이미지 형식입니다.")
    if not any(file_name.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
        file_name += ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_file.write(response.content)
        temp_path = temp_file.name
        with open(temp_path, "rb") as f:
            file_obj = File(f, name=file_name)
            is_valid, errors = validate_upload_data(
                [file_obj],
                date_taken=date_taken_user,
                location=location_user,
                tags=tags,
            )
            if not is_valid:
                raise ValidationError("; ".join(errors))
    return temp_path
