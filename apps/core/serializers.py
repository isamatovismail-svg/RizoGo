from rest_framework import serializers
from .models import User, Driver, Tariff, Trip, Payment, Rating, Delivery, PromoCode, DriverTransaction, ChatMessage

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'role', 'is_phone_verified']

class DriverSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Driver
        fields = [
            'id', 'user', 'car_model', 'car_number', 'car_color',
            'license_number', 'status', 'is_online', 'current_lat',
            'current_lng', 'rating', 'balance'
        ]

class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ['id', 'name', 'base_price', 'price_per_km', 'price_per_minute', 'minimum_price', 'icon']

class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ['id', 'code', 'discount_amount', 'discount_percent', 'is_active']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'method', 'provider', 'amount', 'status', 'transaction_id', 'created_at']

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'client_rating_for_driver', 'driver_rating_for_client', 'client_comment']

class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = ['id', 'package_size', 'receiver_name', 'receiver_phone', 'description']

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'trip', 'sender', 'sender_name', 'message', 'timestamp']

class DriverTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverTransaction
        fields = ['id', 'driver', 'amount', 'transaction_type', 'description', 'created_at']

class TripSerializer(serializers.ModelSerializer):
    client = UserSerializer(read_only=True)
    driver = DriverSerializer(read_only=True)
    tariff = TariffSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)
    rating_data = RatingSerializer(read_only=True)
    delivery_details = DeliverySerializer(read_only=True)
    promo_code = PromoCodeSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id', 'client', 'driver', 'tariff', 'service_type',
            'pickup_address', 'pickup_lat', 'pickup_lng',
            'dropoff_address', 'dropoff_lat', 'dropoff_lng',
            'distance_km', 'surge_multiplier', 'estimated_price',
            'discount_applied', 'final_price', 'promo_code',
            'status', 'scheduled_at', 'created_at', 'completed_at',
            'payment', 'rating_data', 'delivery_details'
        ]
