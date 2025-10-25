from django.urls import path
from .views import (
    RefreshCountriesView, CountryListView,
    CountryDetailView, StatusView, SummaryImageView
)

urlpatterns = [
    path('refresh', RefreshCountriesView.as_view(), name='countries-refresh'),
    path('', CountryListView.as_view(), name='countries-list'),
    path('image/', SummaryImageView.as_view(), name='countries-image'),  # support trailing slash
    path('image', SummaryImageView.as_view()),  # also match without slash
    path('status', StatusView.as_view(), name='countries-status'),
    path('<str:name>', CountryDetailView.as_view(), name='countries-detail'),
]
