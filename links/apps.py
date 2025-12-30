from django.apps import AppConfig


class LinksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'links'

    def ready(self):
        import os
        # 確保只在主進程中啟動，防止 runserver 的 reload 執行兩次
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('ZEABUR'):
            from . import scheduler
            scheduler.start()
