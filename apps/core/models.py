from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('client', 'Mijoz'),
        ('driver', 'Haydovchi'),
        ('dispatcher', 'Dispetcher'),
        ('admin', 'Admin'),
    )
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    is_phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()}) - {self.phone}"


class Driver(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Tasdiqlanmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
        ('blocked', 'Bloklangan'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    car_model = models.CharField(max_length=100)
    car_number = models.CharField(max_length=20)
    car_color = models.CharField(max_length=50)
    license_number = models.CharField(max_length=50)
    license_photo = models.CharField(max_length=255, blank=True, null=True)
    tech_passport_photo = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_online = models.BooleanField(default=False)
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Haydovchi: {self.user.username} [{self.car_model} - {self.car_number}]"


class Tariff(models.Model):
    name = models.CharField(max_length=50)  # Standart, Komfort, Biznes
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_minute = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_price = models.DecimalField(max_digits=10, decimal_places=2)
    icon = models.CharField(max_length=50, default='fa-taxi')

    def __str__(self):
        return f"Tarif: {self.name} (Boshlang'ich: {self.base_price} so'm)"


class PromoCode(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percent = models.PositiveIntegerField(default=0)  # e.g., 10 for 10%
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Promokod: {self.code}"


class Trip(models.Model):
    STATUS_CHOICES = (
        ('searching', 'Haydovchi qidirilmoqda'),
        ('accepted', 'Qabul qilindi'),
        ('arrived', 'Haydovchi yetib keldi'),
        ('in_progress', "Yo'lda"),
        ('completed', 'Yakunlandi'),
        ('cancelled_by_client', 'Mijoz tomonidan bekor qilindi'),
        ('cancelled_by_driver', 'Haydovchi tomonidan bekor qilindi'),
    )
    SERVICE_CHOICES = (
        ('taxi', 'Taksi'),
        ('delivery', 'Yetkazib berish'),
    )
    client = models.ForeignKey(User, related_name='trips', on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, related_name='trips', null=True, blank=True, on_delete=models.SET_NULL)
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT)
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES, default='taxi')
    pickup_address = models.CharField(max_length=255)
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()
    dropoff_address = models.CharField(max_length=255)
    dropoff_lat = models.FloatField()
    dropoff_lng = models.FloatField()
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    surge_multiplier = models.FloatField(default=1.0)
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    promo_code = models.ForeignKey(PromoCode, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='searching')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Safar #{self.id} [{self.get_service_type_display()}] - {self.status}"


class Payment(models.Model):
    METHOD_CHOICES = (
        ('cash', 'Naqd'),
        ('card', 'Karta'),
    )
    PROVIDER_CHOICES = (
        ('payme', 'Payme'),
        ('click', 'Click'),
        ('none', '—'),
    )
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('paid', "To'landi"),
        ('failed', 'Xato'),
    )
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='cash')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='none')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To'lov #{self.id} for Safar #{self.trip.id} - {self.amount} so'm [{self.status}]"


class Rating(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='rating_data')
    client_rating_for_driver = models.PositiveSmallIntegerField(null=True, blank=True)
    driver_rating_for_client = models.PositiveSmallIntegerField(null=True, blank=True)
    client_comment = models.TextField(blank=True)

    def __str__(self):
        return f"Baholash for Safar #{self.trip.id}"


class Delivery(models.Model):
    SIZE_CHOICES = (
        ('small', 'Kichik (xat, hujjat)'),
        ('medium', "O'rta (quti, maishiy buyum)"),
        ('large', 'Katta (yirik jo\'natma)'),
    )
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='delivery_details')
    package_size = models.CharField(max_length=20, choices=SIZE_CHOICES, default='small')
    receiver_name = models.CharField(max_length=100)
    receiver_phone = models.CharField(max_length=20)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"Jo'natma #{self.id} for Safar #{self.trip.id} -> {self.receiver_name}"


class DriverTransaction(models.Model):
    TYPE_CHOICES = (
        ('commission', 'Platforma komissiyasi'),
        ('deposit', 'Hisobni to\'ldirish'),
        ('bonus', 'Rag\'batlantirish bonusi'),
        ('payout', 'Yechib olish'),
    )
    driver = models.ForeignKey(Driver, related_name='transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Positive or negative
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tranzaksiya: {self.driver.user.username} - {self.amount} so'm ({self.transaction_type})"


class ChatMessage(models.Model):
    trip = models.ForeignKey(Trip, related_name='chat_messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat #{self.trip.id} - {self.sender.username}: {self.message[:20]}"
