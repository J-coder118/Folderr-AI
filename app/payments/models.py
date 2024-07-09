from django.db import models


class StripePaymentLink(models.Model):
    plan = models.OneToOneField(
        "djstripe.Plan", on_delete=models.CASCADE, related_name="payment_link"
    )
    url = models.URLField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment link for {self.plan}"

    class Meta:
        db_table = "payment_links"
