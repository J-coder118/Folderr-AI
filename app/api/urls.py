from django.urls import include, path

from .views import (
    ConstactUs,
    GlobalSearch,
    TokenVerify,
    UserCreate,
    UserList,
    check_email,
    is_authenticated,
    list_user_mfa_methods,
    logout,
    obtain_auth_tokens,
    refresh_access_token,
    send_email_2fa_code,
    send_sms_2fa_code,
)

urlpatterns = [
    path("user-exists/<email>", check_email, name="check-email"),
    path("user/", UserCreate.as_view(), name="user-create"),
    path("users/", UserList.as_view(), name="user-list"),
    path("token/", obtain_auth_tokens, name="token_obtain_pair"),
    path("token/refresh/", refresh_access_token, name="token_refresh"),
    path("token/verify/", TokenVerify.as_view(), name="token_verify"),
    path("logout/", logout, name="logout"),
    path("", include("filemanager.urls")),
    path("contact-us/", ConstactUs.as_view(), name="contact-us"),
    path("users/global-search/", GlobalSearch.as_view(), name="global-search"),
    path("is-authenticated/", is_authenticated, name="is-authenticated"),
    path("mfa-methods/", list_user_mfa_methods, name="mfa-methods"),
    path(
        "send-sms-code/<int:sms_id>/", send_sms_2fa_code, name="send-sms-code"
    ),
    path("send-email-code/", send_email_2fa_code, name="send-email-code"),
]
