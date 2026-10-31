from rest_framework import serializers


class CardInputSerializer(serializers.Serializer):
    number = serializers.RegexField(r"^[0-9]{16}$", max_length=16)
    holder = serializers.CharField(max_length=120)
    expiry_month = serializers.IntegerField(min_value=1, max_value=12)
    expiry_year = serializers.IntegerField(min_value=2000, max_value=9999)
    security_code = serializers.RegexField(r"^[0-9]{3}$", max_length=3, trim_whitespace=False)

    def validate_holder(self, value):
        return " ".join(value.split()).upper()

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        if set(data) - set(self.fields):
            raise serializers.ValidationError("La tarjeta contiene campos no admitidos.")
        return attrs


class CheckoutInputSerializer(serializers.Serializer):
    quote_id = serializers.UUIDField()
    card = CardInputSerializer()

    def validate(self, attrs):
        if set(self.initial_data) - {"quote_id", "card"}:
            raise serializers.ValidationError("Solo se admite la cotización y la tarjeta ficticia.")
        return attrs
