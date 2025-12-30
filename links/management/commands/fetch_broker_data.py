import os
import requests
from django.core.management.base import BaseCommand
from links.models import Broker, StockRecord
from links.utils.crawler import generate_fubon_detail_link, fetch_top_buyers
from datetime import datetime


class Command(BaseCommand):
    help = 'Fetch broker stock records from Fubon and store in DB'

    def handle(self, *args, **options):
        brokers = Broker.objects.all()
        if not brokers.exists():
            self.stdout.write(self.style.WARNING(
                'No brokers found in database.'))
            return

        self.stdout.write(f"Starting fetch at {datetime.now()}")

        total_created = 0
        total_updated = 0

        for broker in brokers:
            self.stdout.write(f"Fetching data for broker: {broker.name}")

            # Generate link for daily data (days=1)
            link = generate_fubon_detail_link(
                broker.fbs_a, broker.fbs_b, days=1)

            try:
                buy_data, date_str, sell_data = fetch_top_buyers(
                    link, record_type=1)

                # date_str can be YYYY-MM-DD, YYYY/MM/DD or YYYYMMDD
                try:
                    clean_date_str = date_str.replace('/', '-').strip()
                    if '-' in clean_date_str:
                        record_date = datetime.strptime(
                            clean_date_str, '%Y-%m-%d').date()
                    else:
                        # Handle YYYYMMDD format
                        record_date = datetime.strptime(
                            clean_date_str, '%Y%m%d').date()
                except ValueError:
                    self.stdout.write(self.style.ERROR(
                        f"Could not parse date: {date_str} for {broker.name}"))
                    continue

                all_records = buy_data + sell_data

                for item in all_records:
                    obj, created = StockRecord.objects.update_or_create(
                        broker=broker,
                        stock_code=item['code'],
                        date=record_date,
                        record_type=1,
                        defaults={
                            'stock_name': item['name'],
                            'buy_volume': item['buy'],
                            'sell_volume': item['sell'],
                            'net_volume': item['dif'],
                        }
                    )
                    if created:
                        total_created += 1
                    else:
                        total_updated += 1

                self.stdout.write(self.style.SUCCESS(
                    f"Successfully processed {broker.name} for date {record_date}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Error fetching data for {broker.name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(
            f"Finished. Created {total_created} records, updated {total_updated} records."
        ))
