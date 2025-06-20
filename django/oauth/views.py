from oauth.google_drive import build_google_auth_url, get_google_token_from_code
from oauth.onedrive import build_onedrive_auth_url, get_onedrive_token_from_code

from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def cloud_drive_login(request):
    message = request.session.pop("oauth_message", None)
    if request.method == "POST":
        service = request.POST.get("cloud")
        if service == "google":
            return redirect(build_google_auth_url())
        if service == "onedrive":
            return redirect(build_onedrive_auth_url())
        message = "알 수 없는 서비스 요청입니다."
    return render(
        request,
        "oauth/cloud_drive_login.html",
        {"message": message},
    )


@csrf_exempt
def google_drive_redirect(request):
    code = request.GET.get("code")
    message = None
    if code:
        creds = get_google_token_from_code(code)
        if creds and creds.valid:
            message = "구글 드라이브 인증 성공!"
        else:
            message = "구글 드라이브 인증 실패: 토큰이 유효하지 않습니다."
    else:
        message = "인증 코드가 없습니다."
    # 인증 후 /oauth/로 리다이렉트하며 메시지를 세션에 저장
    request.session["oauth_message"] = message
    return redirect("/oauth/")


@csrf_exempt
def onedrive_redirect(request):
    code = request.GET.get("code")
    message = None
    if code:
        result = get_onedrive_token_from_code(code)
        if "access_token" in result:
            message = "원드라이브 인증 성공!"
        else:
            message = f"원드라이브 인증 실패: {result.get('error_description', 'Unknown error')}"
    else:
        message = "인증 코드가 없습니다."
    request.session["oauth_message"] = message
    return redirect("/oauth/")
