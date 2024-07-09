import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

import facebook
import jwt
import requests
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .register import get_or_create_social_user_returning_tokens

log = logging.getLogger(__name__)

User = get_user_model()

PLATFORM_IOS = "ios"
PLATFORM_WEB = "web"


class FacebookSocialAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()

    def validate(self, attrs):
        data = super().validate(attrs)
        facebook_auth_token = data["access_token"]
        try:
            graph = facebook.GraphAPI(access_token=facebook_auth_token)
            user_data = graph.request("/me?fields=name,email")
        except Exception as e:
            log.exception(e)
            raise serializers.ValidationError(
                "The token is invalid or expired. Please login again."
            )
        return get_or_create_social_user_returning_tokens(
            provider="facebook",
            email=user_data.get("email"),
            first_name=user_data.get("name").split(" ")[0],
            last_name=user_data.get("name").split(" ")[1],
        )


class GoogleSocialAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()

    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            response = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {data['access_token']}"},
            )
            if response.ok:
                google_user_profile = response.json()
                return get_or_create_social_user_returning_tokens(
                    provider="google",
                    email=google_user_profile["email"],
                    first_name=google_user_profile["given_name"],
                    last_name=google_user_profile["family_name"],
                )
        except Exception as e:
            log.exception(e)
        raise ValidationError("Invalid token.")


class SIWAResponseSerializer(serializers.Serializer):
    PLATFORM_CHOICES = ((PLATFORM_IOS, "IOS"), (PLATFORM_WEB, "Web"))
    platform = serializers.ChoiceField(
        choices=PLATFORM_CHOICES, required=False
    )
    code = serializers.CharField()
    id_token = serializers.CharField()

    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    @staticmethod
    def _generate_client_secret(platform=PLATFORM_WEB) -> str:
        now = datetime.utcnow()
        headers = {"alg": "ES256", "kid": settings.SIWA_PKEY_ID}
        if platform == PLATFORM_WEB:
            subject = settings.SIWA_CLIENT_ID
        else:
            subject = settings.SIWA_IOS_CLIENT_ID
        payload = {
            "iss": settings.APPLE_TEAM_ID,
            "iat": now,
            "exp": now + timedelta(hours=1),
            "aud": "https://appleid.apple.com",
            "sub": subject,
        }
        with settings.SIWA_PKEY_PATH.open("r", encoding="utf-8") as fp:
            pkey = fp.read()
        return jwt.encode(payload, pkey, "ES256", headers)

    def _user_is_valid(self) -> tuple[bool, Optional[str]]:
        error = None
        is_valid = False

        client_secret = self._generate_client_secret(
            self.initial_data.get("platform", PLATFORM_WEB)
        )
        if self.initial_data.get("platform", PLATFORM_WEB) == PLATFORM_WEB:
            client_id = settings.SIWA_CLIENT_ID
        else:
            client_id = settings.SIWA_IOS_CLIENT_ID
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": self.initial_data["code"],
            "grant_type": "authorization_code",
            "redirect_uri": settings.SIWA_REDIRECT_URI,
        }
        response = requests.request(
            "POST",
            "https://appleid.apple.com/auth/token",
            data=payload,
        )

        if response.status_code in (200, 201):
            is_valid = True
        else:
            response_data = response.json()
            error = response_data["error_description"]
            log.info(
                "Apple user validation failed. Error code: %s, Error: %s",
                response_data["error"],
                error,
            )
        return is_valid, error

    def _get_apple_pubkey(self) -> RSAPublicKey:
        error_msg = "Error retrieving apple public key."
        kid = jwt.get_unverified_header(self.initial_data["id_token"])["kid"]

        response = requests.get("https://appleid.apple.com/auth/keys")
        if response.status_code == 200:
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise ValidationError(error_msg) from e
        else:
            raise ValidationError(error_msg)

        for d in data["keys"]:
            if d["kid"] == kid:
                jwk = d
                break

        return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

    def _get_verified_identity_data(self) -> dict:
        id_token = self.initial_data["id_token"]
        if self.initial_data.get("platform", PLATFORM_WEB) == PLATFORM_WEB:
            audience = settings.SIWA_CLIENT_ID
        else:
            audience = settings.SIWA_IOS_CLIENT_ID
        try:
            public_key = self._get_apple_pubkey()
            identity_data = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=audience,
                issuer="https://appleid.apple.com",
            )
            return identity_data

        except jwt.PyJWTError as e:
            raise ValidationError("Invalid id_token") from e

    def _get_or_create_user(self) -> User:
        identity_data = self._get_verified_identity_data()
        email = identity_data.get("email")
        user = None
        random_email = False
        if email is None:
            email = secrets.token_urlsafe(8) + "@folderr.com"
            random_email = True
        else:
            try:
                user = User.objects.get(email=email)
                if user.apple_subject is None:
                    user.apple_subject = identity_data["sub"]
                    user.save()
            except User.DoesNotExist:
                pass
        if user is None:
            try:
                user = User.objects.get(apple_subject=identity_data["sub"])
            except User.DoesNotExist:
                first_name = self.validated_data.get("first_name")
                profile_complete = True
                if first_name is None:
                    first_name = "NoFirstName"
                    profile_complete = False
                last_name = self.validated_data.get("last_name")
                if last_name is None:
                    last_name = "NoLastName"
                    profile_complete = False
                user_data = {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_verified": True,
                    "auth_provider": "apple",
                    "apple_subject": identity_data["sub"],
                    "random_email": random_email,
                    "profile_complete": profile_complete
                    and random_email is False,
                }
                user = User(**user_data)
                user.set_unusable_password()
                user.full_clean()
                try:
                    user.save()
                except IntegrityError as e:
                    log.info(
                        "IntegrityError while creating Apple user. Data: %s. Message: "
                        "%s",
                        user_data,
                        e,
                    )
                    raise e
        return user

    def validate(self, attrs) -> dict:
        validated_data = super(SIWAResponseSerializer, self).validate(attrs)
        user_is_valid, error = self._user_is_valid()

        if not user_is_valid:
            log.info(
                "Failed to validate user with code %s. Error: %s",
                validated_data["code"],
                error,
            )
            raise ValidationError(
                "Failed to verify your information with Apple."
            )

        identity_data = self._get_verified_identity_data()
        validated_data["verified_identity_data"] = identity_data
        return validated_data

    def create(self, validated_data) -> dict:
        user = self._get_or_create_user()
        auth_tokens = user.get_auth_tokens()
        user_data = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "refresh": auth_tokens["refresh"],
            "access": auth_tokens["access"],
        }
        if hasattr(user, "avatar"):
            user_data["avatar"] = user.avatar.url
        return user_data
