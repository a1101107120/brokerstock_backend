from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def start():
    scheduler = BackgroundScheduler()
    
    # 定義要執行的任務
    def fetch_data_task():
        try:
            logger.info("Auto-executing fetch_broker_data task...")
            call_command('fetch_broker_data')
            logger.info("Task completed successfully.")
        except Exception as e:
            logger.error(f"Error in scheduled task: {str(e)}")

    # 設定在 18:00 與 23:00 執行 (台灣時間)
    # 注意：伺服器通常使用 UTC 時間，台灣 18:00 = UTC 10:00，23:00 = UTC 15:00
    scheduler.add_job(fetch_data_task, 'cron', hour=10, minute=0, id='fetch_1800', replace_existing=True)
    scheduler.add_job(fetch_data_task, 'cron', hour=15, minute=0, id='fetch_2300', replace_existing=True)
    
    scheduler.start()
    logger.info("Scheduler started. Jobs: 18:00 & 23:00 (Taiwan Time)")

