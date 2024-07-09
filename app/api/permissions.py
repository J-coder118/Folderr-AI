from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission

User = get_user_model()


class TwoFactorAuthentication(BasePermission):
    def has_permission(self, request, view):
        user = get_object_or_404(
            User.objects.all(), email=request.data.get("email")
        )
        if user.requires_2fa:
            code = request.data.get("otp")
            otp_id = request.data.get("otp_id")
            mfa_method = request.data.get("mfa_method")
            if code is None or otp_id is None or mfa_method is None:
                return False
            queryset = None
            if mfa_method == "totp":
                queryset = user.totps
            elif mfa_method == "sms":
                queryset = user.sms_2fas
            elif mfa_method == "email":
                queryset = user.email_2fas

            if queryset is not None:
                totp = get_object_or_404(queryset.all(), pk=int(otp_id))
                if mfa_method == "totp":
                    return totp.verify_totp(code)
                elif mfa_method == "sms" or mfa_method == "email":
                    return totp.check_code(code)
            else:
                return False
        return True


class EmailAndPasswordValid(BasePermission):
    def has_permission(self, request, view):
        user = get_object_or_404(
            User.objects.all(), email=request.data.get("email")
        )
        result = user.check_password(request.data.get("password"))
        if result is True:
            request.user = user
        return result
