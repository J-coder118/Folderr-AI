from django.urls import path

from . import views

app_name = "payments-api"

urlpatterns = [
    path("stripe/payment-link/<int:pk>/", views.RetrieveStripePaymentLink.as_view(),
         name="stripe-payment-link"),
    path("user-is-plus/", views.get_plus_status, name='user-is-plus')
]
