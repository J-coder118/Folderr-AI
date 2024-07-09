from django.urls import include, path
from expenses.api.views import ExpenseViewSet
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r"expenses", ExpenseViewSet, "expenses")

urlpatterns = [path("", include(router.urls))]
