from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.db import transaction
from django.utils import timezone
from django.http import FileResponse, Http404
from django.conf import settings
from django.db.models import Q
from .models import Country
from .serializers import CountrySerializer
from . import utils
import os

SUMMARY_IMAGE_PATH = os.path.join(settings.BASE_DIR, "cache", "summary.png")

class RefreshCountriesView(APIView):
    """
    POST /countries/refresh
    Fetch countries and rates, then save/update DB atomically.
    """
    def post(self, request):
        try:
            countries_raw = utils.fetch_countries()
        except Exception:
            return Response(
                {"error": "External data source unavailable", "details": f"Could not fetch data from Countries API"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        try:
            rates = utils.fetch_rates()
        except Exception:
            return Response(
                {"error": "External data source unavailable", "details": f"Could not fetch data from Exchange Rates API"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Do DB operations inside transaction; if anything fails during processing -> rollback.
        processed = []
        now = timezone.now()
        try:
            with transaction.atomic():
                for c in countries_raw:
                    name = c.get('name')
                    capital = c.get('capital')
                    region = c.get('region')
                    population = c.get('population') or 0
                    flag = c.get('flag')
                    currencies = c.get('currencies') or []

                    # Currency handling rules
                    currency_code = None
                    exchange_rate = None
                    estimated_gdp = None

                    if currencies:
                        first = currencies[0]
                        # currency object shape varies; often { "code": "NGN", ... }
                        currency_code = first.get('code')
                        if currency_code:
                            # Find exchange rate: rates keyed by currency code
                            rate = rates.get(currency_code)
                            if rate is None:
                                # Not found -> set exchange_rate and estimated_gdp to null
                                exchange_rate = None
                                estimated_gdp = None
                            else:
                                exchange_rate = float(rate)
                                estimated_gdp = utils.compute_estimated_gdp(population, exchange_rate)
                        else:
                            # currencies array but no code
                            currency_code = None
                            exchange_rate = None
                            estimated_gdp = 0
                    else:
                        # currencies empty: set currency_code null, exchange_rate null, estimated_gdp 0
                        currency_code = None
                        exchange_rate = None
                        estimated_gdp = 0

                    # Upsert by case-insensitive name
                    try:
                        obj = Country.objects.get(name__iexact=name)
                        # Update all fields
                        obj.capital = capital
                        obj.region = region
                        obj.population = population
                        obj.currency_code = currency_code
                        obj.exchange_rate = exchange_rate
                        obj.estimated_gdp = estimated_gdp
                        obj.flag_url = flag
                        obj.save()
                    except Country.DoesNotExist:
                        obj = Country.objects.create(
                            name=name,
                            capital=capital,
                            region=region,
                            population=population,
                            currency_code=currency_code,
                            exchange_rate=exchange_rate,
                            estimated_gdp=estimated_gdp,
                            flag_url=flag
                        )
                    processed.append(obj)

                # If we reach here, all DB changes committed at transaction end
                # Generate summary image
                total = Country.objects.count()
                # Top 5 by estimated_gdp (largest first). If estimated_gdp null -> treat as -inf
                top = (Country.objects
                       .filter(estimated_gdp__isnull=False)
                       .order_by('-estimated_gdp')[:5])
                top_list = [(c.name, c.estimated_gdp) for c in top]
                # If less than 5 with non-null GDP, include others with None
                if len(top_list) < 5:
                    others = Country.objects.exclude(id__in=[t.id for t in top])[:5-len(top_list)]
                    for c in others:
                        top_list.append((c.name, c.estimated_gdp))
                utils.generate_summary_image(total, top_list, now, SUMMARY_IMAGE_PATH)

                # success; set a global timestamp — we'll use latest last_refreshed_at on records as indicator
                return Response({"status": "success", "total_countries": total, "last_refreshed_at": now}, status=status.HTTP_200_OK)
        except Exception as e:
            # Any exception -> rollback and return 500 (but spec: do not modify DB)
            return Response({"error": "Internal server error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CountryListView(generics.ListAPIView):
    serializer_class = CountrySerializer
    queryset = Country.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        region = self.request.query_params.get('region')
        currency = self.request.query_params.get('currency')
        sort = self.request.query_params.get('sort')  # e.g., gdp_desc or gdp_asc
        if region:
            qs = qs.filter(region__iexact=region)
        if currency:
            qs = qs.filter(currency_code__iexact=currency)
        if sort:
            if sort == 'gdp_desc':
                qs = qs.order_by('-estimated_gdp')
            elif sort == 'gdp_asc':
                qs = qs.order_by('estimated_gdp')
            elif sort == 'name_asc':
                qs = qs.order_by('name')
            elif sort == 'name_desc':
                qs = qs.order_by('-name')
        return qs


class CountryDetailView(APIView):
    def get_object(self, name):
        try:
            return Country.objects.get(name__iexact=name)
        except Country.DoesNotExist:
            return None

    def get(self, request, name):
        obj = self.get_object(name)
        if not obj:
            return Response({"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CountrySerializer(obj)
        return Response(serializer.data)

    def delete(self, request, name):
        obj = self.get_object(name)
        if not obj:
            return Response({"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StatusView(APIView):
    def get(self, request):
        total = Country.objects.count()
        last = Country.objects.order_by('-last_refreshed_at').first()
        last_ts = last.last_refreshed_at if last else None
        return Response({"total_countries": total, "last_refreshed_at": last_ts})


class SummaryImageView(APIView):
    def get(self, request):
        if not os.path.exists(SUMMARY_IMAGE_PATH):
            return Response({"error": "Summary image not found"}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(SUMMARY_IMAGE_PATH, 'rb'), content_type='image/png')
