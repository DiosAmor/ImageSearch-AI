from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from oauth.google_drive import build_google_auth_url
from oauth.utils import get_token

# 파일 크기 변환을 위한 상수
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024


def list_images_in_google_drive(user_email, page_size=20):
    """인증된 사용자의 Google Drive에서 이미지 파일 목록을 가져온다.
    인증이 안 되어 있으면 인증 URL을 반환하는 Exception을 발생시킨다.
    반환: [{'id': ..., 'name': ..., 'webViewLink': ...}, ...]
    """
    access_token = get_token(user_email, "google")
    if not access_token:
        auth_url = build_google_auth_url()
        raise Exception(
            f"Google Drive 인증이 필요합니다. <a href='{auth_url}' class='cloud-auth-link' target='_blank'>Google Drive 인증하기</a>"
        )
    creds = Credentials(token=access_token)
    service = build("drive", "v3", credentials=creds)
    results = (
        service.files()
        .list(
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink)",
            q="mimeType contains 'image/' and trashed = false",
        )
        .execute()
    )
    return results.get("files", [])


def list_folders_and_images_in_google_drive(
    user_email, parent_id=None, is_shared=False, drive_id=None
):
    """인증된 사용자의 Google Drive에서 폴더와 이미지 파일 목록을 함께 가져온다.
    폴더는 상위에, 이미지는 하위에 표시하도록 데이터를 구성한다.

    Args:
        user_email: 사용자 이메일
        parent_id: 상위 폴더 ID (None이면 루트 조회)    Returns:
        folders: 폴더 목록 [{'id': str, 'name': str, 'date': str}]
        images: 이미지 목록 [{'id': str, 'name': str, 'url': str, 'date': str, 'size': str, 'type': str}]
        folder_name: 현재 폴더 이름

    """
    access_token = get_token(user_email, "google")
    if not access_token:
        auth_url = build_google_auth_url()
        raise Exception(
            f"Google Drive 인증이 필요합니다. <a href='{auth_url}' class='cloud-auth-link' target='_blank'>Google Drive 인증하기</a>"
        )
    creds = Credentials(token=access_token)
    service = build("drive", "v3", credentials=creds)

    folder_name = "내 드라이브" if not is_shared else "공유 폴더"
    parent_info = {"parent_id": None, "drive_id": None, "is_shared": is_shared}
    # 공유폴더 탐색이면 driveId와 id로 children API 사용
    if is_shared and parent_id:
        if not drive_id:
            # driveId 없는 공유폴더는 children 탐색 불가
            return [], [], "(공유 폴더 정보 없음)", {"parent_id": None, "drive_id": None, "is_shared": True, "error": "Google Drive 공유폴더의 driveId 정보가 없어 하위 탐색이 불가합니다."}
        try:
            folder = (
                service.files()
                .get(
                    fileId=parent_id,
                    supportsAllDrives=True,
                    fields="name,parents,driveId",
                )
                .execute()
            )
            folder_name = folder.get("name", folder_name)
            parents = folder.get("parents", [])
            parent_info = {
                "parent_id": parents[0] if parents else None,
                "drive_id": folder.get("driveId"),
                "is_shared": True,
            }
        except Exception:
            parent_info = {"parent_id": None, "drive_id": drive_id, "is_shared": True}
        query = f"'{parent_id}' in parents and trashed = false"
        folder_query = f"{query} and mimeType = 'application/vnd.google-apps.folder'"
        image_query = f"{query} and mimeType contains 'image/'"
        folder_results = (
            service.files()
            .list(
                pageSize=100,
                fields="files(id, name, createdTime, modifiedTime, driveId)",
                q=folder_query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="drive",
                driveId=drive_id,
                orderBy="name",
            )
            .execute()
        )
        image_results = (
            service.files()
            .list(
                pageSize=100,
                fields="files(id, name, mimeType, webViewLink, createdTime, modifiedTime, size, driveId)",
                q=image_query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="drive",
                driveId=drive_id,
                orderBy="name",
            )
            .execute()
        )
    else:
        # 내 드라이브(또는 일반 폴더) 탐색
        if parent_id:
            try:
                folder = (
                    service.files()
                    .get(fileId=parent_id, fields="name,parents,driveId")
                    .execute()
                )
                folder_name = folder.get("name", "내 드라이브")
                parents = folder.get("parents", [])
                parent_info = {
                    "parent_id": parents[0] if parents else None,
                    "drive_id": folder.get("driveId"),
                    "is_shared": False,
                }
            except Exception:
                folder_name = "내 드라이브"
                parent_info = {"parent_id": None, "drive_id": None, "is_shared": False}
        else:
            parent_info = {"parent_id": None, "drive_id": None, "is_shared": False}
        query = "trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        else:
            query += " and 'root' in parents"
        folder_query = f"{query} and mimeType = 'application/vnd.google-apps.folder'"
        image_query = f"{query} and mimeType contains 'image/'"
        folder_results = (
            service.files()
            .list(
                pageSize=100,
                fields="files(id, name, createdTime, modifiedTime, driveId)",
                q=folder_query,
                orderBy="name",
            )
            .execute()
        )
        image_results = (
            service.files()
            .list(
                pageSize=100,
                fields="files(id, name, mimeType, webViewLink, createdTime, modifiedTime, size, driveId)",
                q=image_query,
                orderBy="name",
            )
            .execute()
        )
    # 폴더 정보 포맷팅
    folders = []
    for folder in folder_results.get("files", []):
        modified_time = folder.get("modifiedTime", "")
        if modified_time:
            date_obj = datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
        else:
            formatted_date = ""
        folders.append(
            {
                "id": folder.get("id", ""),
                "name": folder.get("name", ""),
                "date": formatted_date,
                "type": "폴더(공유)" if is_shared else "폴더",
                "shared": is_shared,
                "drive_id": folder.get("driveId"),
            }
        )
    # 이미지 정보 포맷팅
    images = []
    for img in image_results.get("files", []):
        modified_time = img.get("modifiedTime", "")
        if modified_time:
            date_obj = datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
        else:
            formatted_date = ""
        size_bytes = int(img.get("size", 0))
        if size_bytes < BYTES_PER_KB:
            size_str = f"{size_bytes} B"
        elif size_bytes < BYTES_PER_MB:
            size_str = f"{size_bytes / BYTES_PER_KB:.1f} KB"
        else:
            size_str = f"{size_bytes / BYTES_PER_MB:.1f} MB"
        mime_type = img.get("mimeType", "")
        file_type = mime_type.split("/")[1] if "/" in mime_type else "파일"
        images.append(
            {
                "id": img.get("id", ""),
                "name": img.get("name", ""),
                "url": img.get("webViewLink", ""),
                "date": formatted_date,
                "size": size_str,
                "type": file_type.upper() + ("(공유)" if is_shared else ""),
                "shared": is_shared,
                "drive_id": img.get("driveId"),
            }
        )
    # 루트에서는 sharedWithMe도 추가
    if not parent_id and not is_shared:
        shared_results = (
            service.files()
            .list(
                q="sharedWithMe and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="files(id, name, createdTime, modifiedTime, driveId, owners)",
                pageSize=100,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                orderBy="name",
            )
            .execute()
        )
        for folder in shared_results.get("files", []):
            # driveId가 없는 공유폴더는 표시하지 않음
            if not folder.get("driveId"):
                continue
            modified_time = folder.get("modifiedTime", "")
            if modified_time:
                date_obj = datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
            else:
                formatted_date = ""
            folders.append(
                {
                    "id": folder.get("id", ""),
                    "name": folder.get("name", "") + " (공유됨)",
                    "date": formatted_date,
                    "type": "폴더(공유)",
                    "shared": True,
                    "drive_id": folder.get("driveId"),
                }
            )
    return folders, images, folder_name, parent_info
