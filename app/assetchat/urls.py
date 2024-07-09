from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

app_name = "assetchat"

router = SimpleRouter()
router.register("chats", views.ChatViewset)

urlpatterns = [
    path(
        "start-training/<int:folder_pk>/",
        views.start_training,
        name="start-training",
    ),
    path(
        "ask-question/<int:folder_pk>/",
        views.ask_question,
        name="ask-question",
    ),
    path("history/<int:chat_pk>/", views.chat_history, name="chat-history"),
    path(
        "training-required/<int:folder_pk>/",
        views.training_required,
        name="training-required",
    ),
    path("usage-limit/", views.get_usage_limit, name="usage-limit"),
] + router.urls
