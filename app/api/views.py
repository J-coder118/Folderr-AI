import jwt
from backend.settings import SIMPLE_JWT
from core.models import User
from core.serializers import (
    ContactUsSerializer,
    UserObtainPairSerializer,
    UserRegisterSerializer,
    UserSearchSerializer,
    UserSerializer,
)
from core.tasks import send_email_otp, send_sms_otp
from core.utils import set_refresh_token_cookie
from django.conf import settings
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .permissions import EmailAndPasswordValid, TwoFactorAuthentication
from .serializers import EmailPasswordSerializer, MFAListSerializer
from .tasks import contact_us

# Create your views here.


@api_view()
@permission_classes([AllowAny])
def check_email(request, email):
    user = get_object_or_404(User, email=email)
    return Response(
        {
            "user": {
                "image": user.avatar.url,
                "userType": "Personal Account",
                "firstName": user.first_name,
                "lastName": user.last_name,
                "requires_mfa": user.requires_2fa,
            }
        }
    )


@api_view(http_method_names=["POST"])
@permission_classes([EmailAndPasswordValid])
def list_user_mfa_methods(request):
    serializer = MFAListSerializer(
        {
            "totps": request.user.totps.filter(active=True),
            "sms": request.user.sms_2fas.filter(active=True),
            "email": request.user.email_2fas.filter(active=True),
        }
    )
    return Response(serializer.data)


class UserCreate(generics.CreateAPIView):
    # permission_classes = [IsAuthenticated]
    serializer_class = UserRegisterSerializer


class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)


class UserObtainPairView(TokenObtainPairView):
    serializer_class = UserObtainPairSerializer
    permission_classes = [TwoFactorAuthentication]


class CustomRefreshTokenView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer


class TokenVerify(APIView):
    def post(self, request):
        try:
            token = request.data.get("token")
            value = jwt.decode(
                token,
                SIMPLE_JWT["SIGNING_KEY"],
                algorithms=[SIMPLE_JWT["ALGORITHM"]],
            )
            if value:
                return Response({"status": "success", "is_active": True})
        except Exception:
            return Response({"status": "error", "is_active": False})


class ConstactUs(generics.GenericAPIView):
    serializer_class = ContactUsSerializer

    def post(self, request):
        payload = {
            "name": request.data.get("name"),
            "email": request.data.get("email"),
            "msg": request.data.get("msg"),
        }
        serializer = self.serializer_class(data=payload)
        if serializer.is_valid():
            contact_us.delay(payload)
            return Response({"success": True}, status=status.HTTP_200_OK)
        else:
            return Response(data={"message": serializer.errors}, status=404)


class GlobalSearch(generics.ListAPIView):
    serializer_class = UserSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        kw = request.query_params.get("search")
        data = []
        if len(kw) >= 3:
            users = User.objects.filter(
                Q(first_name__icontains=kw)
                | Q(last_name__icontains=kw)
                | Q(email__icontains=kw)
            )
            user_serializer = self.serializer_class(users, many=True)
            data = user_serializer.data
        return Response(data)


@api_view()
@permission_classes([IsAuthenticated])
def is_authenticated(request):
    return Response()


@api_view(http_method_names=["POST"])
def send_sms_2fa_code(request, sms_id):
    email = request.data.get("email")
    password = request.data.get("password")
    if email is None or password is None:
        return Response(
            "Please provide email and password.",
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = get_object_or_404(User.objects.all(), email=email)
    if not user.check_password(password):
        return Response("Invalid password.", status=status.HTTP_403_FORBIDDEN)
    sms = get_object_or_404(user.sms_2fas.all(), id=sms_id)
    send_sms_otp(sms.id)
    return Response()


@api_view(http_method_names=["POST"])
def send_email_2fa_code(request):
    email = request.data.get("email")
    password = request.data.get("password")
    if email is None or password is None:
        return Response(
            "Please provide email and password.",
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = get_object_or_404(User.objects.all(), email=email)
    if not user.check_password(password):
        return Response("Invalid password.", status=status.HTTP_403_FORBIDDEN)
    email_2fa = user.email_2fas.first()
    if email_2fa is None:
        raise NotFound("Email 2FA not found")
    send_email_otp(email_2fa.id)
    return Response()


@api_view(http_method_names=["POST"])
@permission_classes([TwoFactorAuthentication])
def obtain_auth_tokens(request):
    auth_serializer = EmailPasswordSerializer(data=request.data)
    auth_serializer.is_valid(raise_exception=True)
    data = {"access": auth_serializer.validated_data["tokens"]["access"]}
    if auth_serializer.validated_data.get("bypass_token"):
        data["refresh"] = auth_serializer.validated_data["tokens"]["refresh"]
    response = Response(data=data)
    if auth_serializer.validated_data["remember"]:
        refresh_token_expiry = settings.SESSION_COOKIE_AGE
    else:
        refresh_token_expiry = 0
    response = set_refresh_token_cookie(
        response,
        auth_serializer.validated_data["tokens"]["refresh"],
        refresh_token_expiry,
    )
    return response


@api_view(http_method_names=["POST"])
def refresh_access_token(request):
    try:
        provided_token = request.COOKIES.get(
            settings.REFRESH_TOKEN_COOKIE_NAME
        )
        if provided_token is None:
            provided_token = request.data.get("refresh", "")
        refresh = RefreshToken(provided_token)
    except TokenError:
        return Response(
            {
                "detail": "Session expired.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return Response({"access": str(refresh.access_token)})


@api_view(http_method_names=["POST"])
def logout(request):
    response = Response()
    response.delete_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME,
        "/",
        settings.REFRESH_TOKEN_COOKIE_DOMAIN,
        settings.REFRESH_TOKEN_COOKIE_SAMESITE,
    )
    return response
