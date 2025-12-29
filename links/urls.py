from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BrokerViewSet, LiveCrawlerView, HistoryCrawlerView, StockRecordStatsView

router = DefaultRouter()
router.register(r'brokers', BrokerViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('crawler/live/', LiveCrawlerView.as_view(), name='live-crawler'),
    path('crawler/history/', HistoryCrawlerView.as_view(), name='history-crawler'),
    path('records/stats/', StockRecordStatsView.as_view(), name='record-stats'),
]

