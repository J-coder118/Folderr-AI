import pyotp
from core.models import SMS2FA, TOTP, Email2FA
from rest_framework import permissions


class UpdateProfilePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return obj == request.user


class ProvidedValidTotp(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.basename == "totp":
            queryset = request.user.totps
            model = TOTP
        elif view.basename == "sms2fa":
            queryset = request.user.sms_2fas
            model = SMS2FA
        elif view.basename == "email2fa":
            queryset = request.user.email_2fas
            model = Email2FA
        else:
            raise Exception("Unknown view name.")
        if request.method == "POST":
            return True
        elif request.method not in permissions.SAFE_METHODS:
            otp_id = view.kwargs.get("pk")
            user_otp = request.data.get("otp")
            if user_otp is None or otp_id is None:
                return False
            try:
                totp = queryset.get(pk=otp_id)
            except model.DoesNotExist:
                return False
            totp_verifier = pyotp.totp.TOTP(totp.secret, interval=120)

            result = totp_verifier.verify(user_otp)

            if result is False and view.basename == "totp":
                in_backup = user_otp in totp.backup_codes
                if in_backup:
                    totp.backup_codes.remove(user_otp)
                    totp.save()
                    return True
                return False
            return result
        return True


class IsTotpOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.user == request.user:
            return True
        return False
