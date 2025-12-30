from rest_framework import viewsets, views, response, status
from links.models import Broker, StockRecord
from links.serializers import BrokerSerializer
from links.utils.crawler import (
    generate_fubon_link, generate_fubon_detail_link, generate_histock_link,
    fetch_top_buyers, get_merged_data, find_previous_workdays_range,
    get_main_force_merged_data, fetch_stock_main_force_data
)
from datetime import datetime


class BrokerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Broker.objects.all()
    serializer_class = BrokerSerializer


class LiveCrawlerView(views.APIView):
    def get(self, request):
        number = request.query_params.get('number', '').strip()
        brokers = Broker.objects.all()
        if not brokers.exists():
            return response.Response({"error": "No brokers found in database"}, status=status.HTTP_404_NOT_FOUND)

        results = []
        total_buy = 0
        total_sell = 0
        total_net = 0

        for broker in brokers:
            fubon_link = generate_fubon_link(
                number, broker.fbs_a, broker.fbs_b) if number else ""
            fubon_detail_ranking = generate_fubon_detail_link(
                broker.fbs_a, broker.fbs_b)
            histock_link = generate_histock_link(
                number, broker.stock_bno) if number else ""

            # 1. Fetch daily top data first to get the current trading date
            try:
                buy_data, date, sell_data = get_merged_data(
                    broker.fbs_a, broker.fbs_b, broker.name)
            except Exception as e:
                print(f"Error crawling daily data for {broker.name}: {e}")
                buy_data, date, sell_data = [], "Error", []

            # 2. Fetch specific stats for the searched stock number using the same date
            specific_stats = None
            if number and date != "Error":
                try:
                    # Fetch from zco0 and filter by the identified date
                    data = get_main_force_merged_data(
                        number, broker.fbs_a, broker.fbs_b, date)
                    if data:
                        net_val = data.get('net', 0)
                        specific_stats = {
                            "buy": data.get('buy', 0),
                            "sell": data.get('sell', 0),
                            "net": f"+{net_val}" if net_val > 0 else str(net_val)
                        }
                        total_buy += data.get('buy', 0)
                        total_sell += data.get('sell', 0)
                        total_net += net_val
                except Exception as e:
                    print(
                        f"Error fetching specific stats for {number} at {broker.name}: {e}")

            results.append({
                "broker_name": broker.name,
                "fubon_link": fubon_link,
                "fubon_ranking_link": fubon_detail_ranking,
                "histock_link": histock_link,
                "buy_data": buy_data,
                "sell_data": sell_data,
                "specific_stats": specific_stats,
                "date": date,
                "stock_bno": broker.stock_bno,
                "fbs_a": broker.fbs_a,
                "fbs_b": broker.fbs_b
            })

        return response.Response({
            "stock_number": number,
            "brokers_data": results,
            "total_stats": {
                "buy": total_buy,
                "sell": total_sell,
                "net": f"+{total_net}" if total_net > 0 else str(total_net)
            } if number else None
        })


class DatabaseLiveCrawlerView(views.APIView):
    def get(self, request):
        number = request.query_params.get('number', '').strip()
        date_str = request.query_params.get(
            'date', datetime.now().strftime("%Y-%m-%d"))

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return response.Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        brokers = Broker.objects.all()
        if not brokers.exists():
            return response.Response({"error": "No brokers found in database"}, status=status.HTTP_404_NOT_FOUND)

        results = []
        total_buy = 0
        total_sell = 0
        total_net = 0

        BROKER_CONDITIONS = {
            "港商麥格理": {"buy_threshold": 300, "sell_threshold": -300},
            "default": {"buy_threshold": 60, "sell_threshold": -60},
        }

        for broker in brokers:
            fubon_link = generate_fubon_link(
                number, broker.fbs_a, broker.fbs_b) if number else ""
            fubon_detail_ranking = generate_fubon_detail_link(
                broker.fbs_a, broker.fbs_b)
            histock_link = generate_histock_link(
                number, broker.stock_bno) if number else ""

            # Fetch records from DB
            records = StockRecord.objects.filter(
                broker=broker, date=target_date)

            thresholds = BROKER_CONDITIONS.get(
                broker.name, BROKER_CONDITIONS["default"])

            buy_records = records.filter(
                net_volume__gte=thresholds["buy_threshold"]).order_by('-net_volume')
            sell_records = records.filter(
                net_volume__lte=thresholds["sell_threshold"]).order_by('net_volume')

            buy_data = [{
                'name': r.stock_name,
                'code': r.stock_code,
                'buy': r.buy_volume,
                'sell': r.sell_volume,
                'dif': r.net_volume,
                'date': str(r.date)
            } for r in buy_records]

            sell_data = [{
                'name': r.stock_name,
                'code': r.stock_code,
                'buy': r.buy_volume,
                'sell': r.sell_volume,
                'dif': r.net_volume,
                'date': str(r.date)
            } for r in sell_records]

            # Specific stats for searched stock
            specific_stats = None
            if number:
                specific_record = records.filter(stock_code=number).first()
                if specific_record:
                    net_val = specific_record.net_volume
                    specific_stats = {
                        "buy": specific_record.buy_volume,
                        "sell": specific_record.sell_volume,
                        "net": f"+{net_val}" if net_val > 0 else str(net_val)
                    }
                    total_buy += specific_record.buy_volume
                    total_sell += specific_record.sell_volume
                    total_net += net_val

            results.append({
                "broker_name": broker.name,
                "fubon_link": fubon_link,
                "fubon_ranking_link": fubon_detail_ranking,
                "histock_link": histock_link,
                "buy_data": buy_data,
                "sell_data": sell_data,
                "specific_stats": specific_stats,
                "date": date_str,
                "stock_bno": broker.stock_bno,
                "fbs_a": broker.fbs_a,
                "fbs_b": broker.fbs_b
            })

        return response.Response({
            "stock_number": number,
            "brokers_data": results,
            "total_stats": {
                "buy": total_buy,
                "sell": total_sell,
                "net": f"+{total_net}" if total_net > 0 else str(total_net)
            } if number else None,
            "is_from_db": True
        })


class StockMainForceCrawlerView(views.APIView):
    def get(self, request):
        number = request.query_params.get('number', '').strip()
        if not number:
            return response.Response({"error": "Stock number is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get current date in YYYY-MM-DD format
        date_str = datetime.now().strftime("%Y-%m-%d")

        try:
            data = fetch_stock_main_force_data(number, date_str)
            if not data:
                return response.Response({"error": "Failed to fetch stock main force data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return response.Response({
                "stock_number": number,
                "date": data["date"],
                "buy_list": data["buy_list"],
                "sell_list": data["sell_list"]
            })
        except Exception as e:
            print(f"Error in StockMainForceCrawlerView: {e}")
            return response.Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
