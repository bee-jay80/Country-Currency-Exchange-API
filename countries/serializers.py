from rest_framework import serializers
from .models import Country

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            "id", "name", "capital", "region", "population",
            "currency_code", "exchange_rate", "estimated_gdp",
            "flag_url", "last_refreshed_at"
        ]

    def validate(self, data):
        errors = {}
        # On create/update through API validate required fields
        # For endpoints that accept DB data, ensure required exist
        name = data.get('name') or getattr(self.instance, 'name', None)
        population = data.get('population') or getattr(self.instance, 'population', None)
        currency_code = data.get('currency_code') or getattr(self.instance, 'currency_code', None)

        if not name:
            errors['name'] = 'is required'
        if population in (None, ''):
            errors['population'] = 'is required'
        if currency_code in (None, ''):
            errors['currency_code'] = 'is required'

        if errors:
            raise serializers.ValidationError({"error": "Validation failed", "details": errors})
        return data
