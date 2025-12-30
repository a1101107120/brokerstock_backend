from django.db import models

class Broker(models.Model):
    name = models.CharField(max_length=100, unique=True)
    fbs_a = models.CharField(max_length=50)
    fbs_b = models.CharField(max_length=100)
    stock_bno = models.CharField(max_length=50)

    def __str__(self):
        return self.name

