from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from oauth.google_drive import build_google_auth_url
from oauth.utils import get_token


def list_images_in_google_drive(user_email, page_size=20):
    """인증된 사용자의 Google Drive에서 이미지 파일 목록을 가져온다.
    인증이 안 되어 있으면 인증 URL을 반환하는 Exception을 발생시킨다.
    반환: [{'id': ..., 'name': ..., 'webViewLink': ...}, ...]
    """
    access_token = get_token(user_email, "google")
    if not access_token:
        auth_url = build_google_auth_url()
        raise Exception(
            f"Google Drive 인증이 필요합니다. <a href='{auth_url}' target='_blank'>Google Drive 인증하기</a>"
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
    files = results.get("files", [])
    return files
