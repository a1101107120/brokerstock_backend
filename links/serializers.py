from rest_framework import serializers
from .models import Broker, StockRecord

class BrokerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Broker
        fields = '__all__'

class StockRecordSerializer(serializers.ModelSerializer):
    broker_name = serializers.ReadOnlyField(source='broker.name')
    
    class Meta:
        model = StockRecord
        fields = '__all__'

