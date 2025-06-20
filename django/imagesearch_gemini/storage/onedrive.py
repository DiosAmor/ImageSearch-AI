import requests
from oauth.onedrive import build_onedrive_auth_url
from oauth.utils import get_token


def list_images_in_onedrive(user_email, top=20):
    """인증된 사용자의 OneDrive에서 이미지 파일 목록을 가져온다.
    인증이 안 되어 있으면 인증 URL을 반환하는 Exception을 발생시킨다.
    반환: [{'id': ..., 'name': ..., 'webUrl': ...}, ...]
    """
    access_token = get_token(user_email, "onedrive")
    if not access_token:
        auth_url = build_onedrive_auth_url()
        # 올바른 OneDrive 인증 URL을 안내
        raise Exception(
            f"OneDrive 인증이 필요합니다. <a href='{auth_url}' target='_blank'>OneDrive 인증하기</a>"
        )
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    url = f"https://graph.microsoft.com/v1.0/me/drive/root/children?$top={top}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        items = response.json().get("value", [])
        return items
    raise Exception(f"OneDrive 목록 조회 실패: {response.text}")
