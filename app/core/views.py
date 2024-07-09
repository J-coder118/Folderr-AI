import json
import logging
import random
import tempfile
from datetime import datetime, timedelta

from celery.result import AsyncResult
from core.permissions import (
    IsTotpOwner,
    ProvidedValidTotp,
    UpdateProfilePermission,
)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from filemanager.models import Folder
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import SMS2FA, TOTP, Email2FA, FolderrEmail
from .serializers import (
    ChangePasswordSerializer,
    Email2FASerializer,
    FolderrEmailSerializer,
    OTPValidateSerializer,
    PasswordResetConfirmOTPSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetEmailSerializer,
    PasswordResetOTPSerializer,
    SMS2FASerializer,
    TOTPSerializer,
    UpdateProfileAvatar,
    UpdateProfileSerializer,
    UserSerializer,
)
from .tasks import (
    fetch_mail_from_s3,
    process_email_task,
    send_email_otp,
    send_sms_otp,
    task_otp_for_password_reset,
)

log = logging.getLogger(__name__)

User = get_user_model()


# Create your views here.
class PasswordResetEmail(generics.GenericAPIView):
    serializer_class = PasswordResetEmailSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response({"success": True}, status=status.HTTP_200_OK)


class PasswordResetOTP(generics.GenericAPIView):
    serializer_class = PasswordResetOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        phone_number = self.request.data.get("phone_number")
        if phone_number:
            try:
                user = User.objects.get(phone_number=phone_number)
            except Exception:
                return Response(
                    {"status": "error", "message": "Record Not Found."}
                )
            otp = random.randint(100000, 999999)
            sms_body = f"OTP for reset password is {otp}, please do not disclose with any one else."
            User.objects.filter(id=user.id).update(
                otp=otp, otp_expires=datetime.utcnow() + timedelta(minutes=15)
            )
            # TODO Send OTP.
            task_otp_for_password_reset.delay(
                phone_number=phone_number, sms_body=sms_body
            )
        return Response({"success": True}, status=status.HTTP_200_OK)


class MobileNumberVerify(APIView):
    def post(self, request):
        phone_number = self.request.data.get("phone_number")
        otp = random.randint(100000, 999999)
        sms_body = f"OTP for account verification is {otp}, please do not disclose with any one else."
        # TODO Send OTP.
        task_otp_for_password_reset.delay(
            phone_number=phone_number, sms_body=sms_body
        )
        return Response({"success": True}, status=status.HTTP_200_OK)


class ValidateOTP(generics.GenericAPIView):
    serializer_class = OTPValidateSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            return Response({"success": True}, status=status.HTTP_200_OK)

        except Exception:
            return Response({"status": "error", "message": serializer.errors})


class PasswordResetConfirm(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, uidb64, token, format=None):
        serializer = self.serializer_class(
            data=request.data, context={"uidb64": uidb64, "token": token}
        )
        serializer.is_valid(raise_exception=True)
        return Response({"success": True}, status=status.HTTP_200_OK)


class PasswordResetConfirmOTP(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
            return Response({"success": True}, status=status.HTTP_200_OK)

        except Exception:
            return Response({"status": "error", "message": serializer.errors})


class UpdateProfile(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UpdateProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        user = self.request.user
        instance = User.objects.get(email=user)
        serializer = self.serializer_class(
            instance, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data})
        else:
            return Response({"status": "error", "message": serializer.errors})

    def delete(self, request, *args, **kargs):
        try:
            user = self.request.user
            User.objects.filter(id=user.id).delete()
            return Response(
                {"status": "success", "data": "user delete successfully"}
            )
        except Exception as e:
            return Response({"status": "error", "message": str(e)})


class UpdateAvatarViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UpdateProfileAvatar
    permission_classes = [UpdateProfilePermission]

    def list(self, request):
        queryset = User.objects.filter(email=self.request.user)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        current_user = self.get_object()
        serializer = self.serializer_class(
            current_user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data})
        else:
            return Response({"status": "error", "message": serializer.errors})


class ChangePasswordViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = ChangePasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True}, status=status.HTTP_200_OK)
        return Response({"status": "error", "message": serializer.errors})


@csrf_exempt
def email_sns_endpoint(request):
    decoded_body = request.body.decode("utf-8")
    log.debug(decoded_body)
    body = json.loads(decoded_body)
    request_type = body["Type"]
    message_id = body["MessageId"]
    if request_type == "Notification":
        message = json.loads(body["Message"])
        log.info("New notification %s", message_id)
        mail = message.get("mail")
        if mail:
            receipt = message["receipt"]
            spam = receipt["spamVerdict"]["status"]
            virus = receipt["virusVerdict"]["status"]
            if spam != "PASS" or virus != "PASS":
                log.info("Message %s contains spam or virus.", message_id)
            else:
                action = receipt["action"]
                action_type = action["type"]
                if action_type == "S3":
                    arn = action["topicArn"]
                    if arn == settings.FODLER_EMAIL_SNS_TOPIC_ARN:
                        object_key = action["objectKey"]
                        try:
                            folderr_email = FolderrEmail.objects.get(
                                s3_object_key=object_key
                            )
                            log.info(
                                "FolderrEmail with object key %s already exists with pk %d",
                                object_key,
                                folderr_email.pk,
                            )
                        except FolderrEmail.DoesNotExist:
                            log.info("Email is in object %s", object_key)
                            fetch_mail_from_s3.delay(object_key)
                    else:
                        log.info(
                            "Received action with arn %s which isn't the same as ours.",
                            arn,
                        )
                else:
                    log.info(
                        "Message %s contains non S3 action. Type: %s",
                        action_type,
                    )
        else:
            log.info("Received non mail notification. Id: %s", message_id)
    elif request_type == "SubscriptionConfirmation":
        log.info("Subscription confirmation notification %s", message_id)
        message = body["Message"]
        message += f"\n\nSubscribeURL: {body['SubscribeURL']}"
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False
        ) as fp:
            fp.write(message)
            log.info("Subscription confirmation message saved to %s", fp.name)
    else:
        log.warning(
            "Received unknown notification type %s. ID: %s",
            request_type,
            message_id,
        )

    return HttpResponse("OK")


class FolderrEmailViewSet(viewsets.ModelViewSet):
    serializer_class = FolderrEmailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        default_qs = self.request.user.folderr_emails.all().order_by(
            "-created_at"
        )
        order_by = self.request.query_params.get("order-by")
        if order_by is not None:
            if order_by == "oldest":
                default_qs = default_qs.order_by("created_at")

        selected_folder_id = self.request.query_params.get("folder")
        if selected_folder_id:
            folder = Folder.objects.get(pk=selected_folder_id)
            qs = default_qs.filter(asset_id=selected_folder_id)
            for sub_folder in folder.subfolders.all():
                qs = qs | default_qs.filter(asset_id=sub_folder.pk)
        else:
            qs = default_qs
        return qs

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance: FolderrEmail = self.get_object()
        instance.status = instance.PROCESSING
        instance.save()
        process_email_task.delay(instance.pk)

    def perform_create(self, serializer):
        if self.request.user.can_receive_email:
            return super().perform_create(serializer)
        raise PermissionDenied("Can't receive any more emails on Free tier.")


class RetrieveUserView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class TOTPViewSet(ModelViewSet):
    queryset = TOTP.objects.all()
    serializer_class = TOTPSerializer
    permission_classes = [IsAuthenticated, ProvidedValidTotp, IsTotpOwner]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk: int):
        totp = get_object_or_404(request.user.totps.all(), pk=pk)
        return Response(totp.verify_totp(request.data.get("code")))


class SMS2FAViewSet(ModelViewSet):
    queryset = SMS2FA.objects.all()
    serializer_class = SMS2FASerializer
    permission_classes = [IsAuthenticated, IsTotpOwner, ProvidedValidTotp]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=["POST"])
    def verify(self, request, pk: int):
        sms_2fa = get_object_or_404(request.user.sms_2fas.all(), pk=pk)
        return Response(sms_2fa.check_code(request.data.get("code")))

    @action(detail=True, methods=["POST"])
    def send_code(self, request, pk: int):
        sms_2fa: SMS2FA = get_object_or_404(request.user.sms_2fas.all(), pk=pk)
        send_sms_otp.delay(sms_2fa.pk)
        return Response()


class Email2FAViewSet(ModelViewSet):
    queryset = Email2FA.objects.all()
    serializer_class = Email2FASerializer
    permission_classes = [IsAuthenticated, IsTotpOwner, ProvidedValidTotp]

    def create(self, request, *args, **kwargs):
        if self.request.user.email_2fas.count() > 0:
            return Response(
                {"detail": "You already activated email 2FA."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=["POST"])
    def verify(self, request, pk: int):
        email_2fa = get_object_or_404(request.user.email_2fas.all(), pk=pk)
        return Response(email_2fa.check_code(request.data.get("code")))

    @action(detail=True, methods=["POST"])
    def send_code(self, request, pk: int):
        email_2fa = get_object_or_404(request.user.email_2fas.all(), pk=pk)
        send_email_otp.delay(email_2fa.pk)
        return Response()


@api_view()
@permission_classes([IsAuthenticated])
def get_background_task_result(request, task_id: str):
    result = AsyncResult(task_id)
    if result is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    response_body = {"failed": False, "result": None}
    if result.failed():
        response_body["failed"] = True
    elif result.successful():
        data = result.get()
        user_id = data.get("user_id", None)
        if user_id is not None:
            if request.user.id != user_id:
                return Response(status=status.HTTP_403_FORBIDDEN)
        response_body["result"] = data["contents"]
    return Response(response_body)
