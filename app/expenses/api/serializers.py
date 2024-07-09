from rest_framework import serializers

from expenses.models import Expense


class ExpenseSerializer(serializers.ModelSerializer):

    def to_representation(self, instance: Expense):
        ret = super(ExpenseSerializer, self).to_representation(instance)
        ret['line_item_headers'] = instance.line_item_headers
        return ret

    class Meta:
        model = Expense
        fields = "__all__"
