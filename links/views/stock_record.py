from rest_framework import views, response, status
from django.db.models import Sum
from ..models import StockRecord
from ..serializers import StockRecordSerializer

class StockRecordStatsView(views.APIView):
    def get(self, request):
        stats = StockRecord.objects.values('stock_code', 'stock_name').annotate(
            total_buy=Sum('buy_volume'),
            total_sell=Sum('sell_volume'),
            total_net=Sum('net_volume')
        ).order_by('-total_net')
        return response.Response(stats)

    def post(self, request):
        serializer = StockRecordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

