from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(
    "change-password", views.ChangePasswordViewSet, basename="change-password"
),
router.register(
    "update-avatar", views.UpdateAvatarViewSet, basename="update-avatar"
)
router.register(
    "folderr-emails", views.FolderrEmailViewSet, basename="folderr-emails"
)
router.register("totps", views.TOTPViewSet)
router.register("sms2fas", views.SMS2FAViewSet)
router.register("email2fas", views.Email2FAViewSet)
urlpatterns = [
    path("", include(router.urls)),
    path(
        "reset-password-email",
        views.PasswordResetEmail.as_view(),
        name="reset-password-email",
    ),
    path(
        "reset-password-confirm/<uidb64>/<token>",
        views.PasswordResetConfirm.as_view(),
        name="reset-password-confirm",
    ),
    path(
        "profile/update", views.UpdateProfile.as_view(), name="update-profile"
    ),
    path(
        "reset-password-otp",
        views.PasswordResetOTP.as_view(),
        name="reset-password-otp",
    ),
    path(
        "reset-password-validate-otp",
        views.ValidateOTP.as_view(),
        name="validate-otp",
    ),
    path(
        "reset-password-otp-confirm",
        views.PasswordResetConfirmOTP.as_view(),
        name="reset-password-confirm-otp",
    ),
    path(
        "mobile-number-verify",
        views.MobileNumberVerify.as_view(),
        name="mobile-number-verify",
    ),
    path("user/", views.RetrieveUserView.as_view(), name="retrieve-user"),
    path(
        "background-task-result/<str:task_id>/",
        views.get_background_task_result,
        name="background-task-result",
    )
    # path('', .as_view(), name='mobile-number-verify'),
]
