from django.db import models

class Broker(models.Model):
    name = models.CharField(max_length=100, unique=True)
    fbs_a = models.CharField(max_length=50)
    fbs_b = models.CharField(max_length=100)
    stock_bno = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class StockRecord(models.Model):
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='records')
    stock_code = models.CharField(max_length=20)
    stock_name = models.CharField(max_length=100, blank=True)
    date = models.DateField()
    buy_volume = models.IntegerField(default=0)
    sell_volume = models.IntegerField(default=0)
    net_volume = models.IntegerField(default=0)
    record_type = models.IntegerField(default=1) # 1 for standard, 2 for weighted/special

    class Meta:
        unique_together = ('broker', 'stock_code', 'date', 'record_type')

    def __str__(self):
        return f"{self.date} - {self.broker.name} - {self.stock_code}"
