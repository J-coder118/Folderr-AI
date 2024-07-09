"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from core.views import email_sns_endpoint
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("core.urls")),
    path("api/", include("api.urls")),
    path("filemanager/", include("filemanager.urls")),
    path("expenses/", include("expenses.urls")),
    path("realestate/", include("realestate.urls")),
    path("api/social_auth/", include("social_auth.urls")),
    path(
        "sns-email-subscription/",
        email_sns_endpoint,
        name="email-sns-subscription",
    ),
    path("help/api/", include("help.api.urls")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path("payments/", include("payments.urls")),
    path("sunrun/", include("sunrun.urls")),
    path("asset-ai/", include("assetchat.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler500 = "rest_framework.exceptions.server_error"
handler400 = "rest_framework.exceptions.bad_request"
