from core.models import User
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    User.objects.filter(email=user).update(last_login=timezone.now())
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def get_or_create_social_user_returning_tokens(
    provider, email, first_name, last_name
):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        user = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }
        user = User.objects.create_user(**user)
        user.is_verified = True
        user.auth_provider = provider
        user.set_unusable_password()
        user.save()
    return user.get_auth_tokens()
