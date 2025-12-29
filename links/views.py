from rest_framework import viewsets, views, response, status
from .models import Broker, StockRecord
from .serializers import BrokerSerializer, StockRecordSerializer
from .utils.crawler import (
    generate_fubon_link, generate_fubon_detail_link, generate_histock_link,
    fetch_top_buyers, get_merged_data, find_previous_workdays_range
)
from django.db.models import Sum, F
from datetime import datetime

class BrokerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Broker.objects.all()
    serializer_class = BrokerSerializer

class LiveCrawlerView(views.APIView):
    def get(self, request):
        number = request.query_params.get('number', '').strip()
        # We allow number to be optional now, or default to a common one if needed, 
        # but the links will use this number if provided.
        
        brokers = Broker.objects.all()
        if not brokers.exists():
            return response.Response({"error": "No brokers found in database"}, status=status.HTTP_404_NOT_FOUND)
            
        results = []
        
        for broker in brokers:
            # If number is empty, these links might be partial but shouldn't crash
            fubon_link = generate_fubon_link(number, broker.fbs_a, broker.fbs_b) if number else ""
            fubon_detail_ranking = generate_fubon_detail_link(broker.fbs_a, broker.fbs_b)
            histock_link = generate_histock_link(number, broker.stock_bno) if number else ""
            
            try:
                # This mimics the mergeData logic from original Flask code
                buy_data, date, sell_data = get_merged_data(broker.fbs_a, broker.fbs_b, broker.name)
            except Exception as e:
                print(f"Error crawling data for {broker.name}: {e}")
                buy_data, date, sell_data = [], "Error", []
            
            results.append({
                "broker_name": broker.name,
                "fubon_link": fubon_link,
                "fubon_ranking_link": fubon_detail_ranking,
                "histock_link": histock_link,
                "buy_data": buy_data,
                "sell_data": sell_data,
                "date": date,
                "stock_bno": broker.stock_bno,
                "fbs_a": broker.fbs_a,
                "fbs_b": broker.fbs_b
            })
            
        return response.Response({
            "stock_number": number,
            "brokers_data": results
        })

class HistoryCrawlerView(views.APIView):
    def get(self, request):
        a = request.query_params.get('a')
        b = request.query_params.get('b')
        days = request.query_params.get('days', 5)
        name = request.query_params.get('name', 'Unknown')
        mark = request.query_params.get('mark', '')
        
        try:
            days = int(days)
        except ValueError:
            days = 5
            
        link = generate_fubon_detail_link(a, b, days)
        buy_data, date, sell_data = fetch_top_buyers(link)
        
        date_range = find_previous_workdays_range(date, days)
        
        # Add histock links to items
        for item in buy_data:
            item['histock_link'] = generate_histock_link(item['code'], mark)
        for item in sell_data:
            item['histock_link'] = generate_histock_link(item['code'], mark)
            
        return response.Response({
            "broker_name": name,
            "date": date,
            "date_range": date_range,
            "buy_data": buy_data,
            "sell_data": sell_data,
            "days": days
        })

class StockRecordStatsView(views.APIView):
    def get(self, request):
        # Mimic the /record logic: Aggregate net_volume by stock_code
        stats = StockRecord.objects.values('stock_code', 'stock_name').annotate(
            total_buy=Sum('buy_volume'),
            total_sell=Sum('sell_volume'),
            total_net=Sum('net_volume')
        ).order_by('-total_net')
        
        # We can also group by some category if needed, but original code 
        # seemed to group by columns which we can translate to dates or brokers.
        # For now, let's just return the aggregated stats.
        return response.Response(stats)

    def post(self, request):
        # Add a new record (replaces manual Google Sheet entry)
        serializer = StockRecordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
