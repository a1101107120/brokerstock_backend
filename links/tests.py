from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from datetime import datetime

class StockMainForceCrawlerTests(APITestCase):
    def test_stock_main_force_crawler_no_number(self):
        """測試未提供股票代碼時應回傳 400"""
        url = reverse('stock-main-force-crawler')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Stock number is required")

    @patch('links.views.broker.fetch_stock_main_force_data')
    def test_stock_main_force_crawler_success(self, mock_fetch):
        """測試成功抓取資料時的 API 回傳格式"""
        # 模擬爬蟲回傳的資料
        mock_fetch.return_value = {
            "date": "2025-12-30",
            "buy_list": [
                {"name": "測試券商A", "buy": 100, "sell": 10, "net": 90, "percent": "0.5%"}
            ],
            "sell_list": [
                {"name": "測試券商B", "buy": 10, "sell": 100, "net": -90, "percent": "0.5%"}
            ]
        }
        
        url = reverse('stock-main-force-crawler')
        response = self.client.get(url, {'number': '2330'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stock_number'], '2330')
        self.assertEqual(response.data['date'], '2025-12-30')
        self.assertTrue(len(response.data['buy_list']) > 0)
        self.assertEqual(response.data['buy_list'][0]['name'], "測試券商A")

    def test_real_crawler_call(self):
        """
        如果要進行真實的網路爬蟲測試（不使用 Mock），可以取消註解這段。
        注意：這會依賴外部網路與富邦網站狀態。
        """
        # url = reverse('stock-main-force-crawler')
        # response = self.client.get(url, {'number': '2330'})
        # print(f"\nReal Crawler Result for 2330: {response.data}")
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        pass
