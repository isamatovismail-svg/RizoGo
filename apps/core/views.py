import math
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Count, Q

from .models import User, Driver, Tariff, Trip, Payment, Rating, Delivery, PromoCode, DriverTransaction, ChatMessage
from .serializers import (
    UserSerializer, DriverSerializer, TariffSerializer,
    TripSerializer, PaymentSerializer, RatingSerializer, DeliverySerializer,
    PromoCodeSerializer, DriverTransactionSerializer, ChatMessageSerializer
)

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


# --- AUTH ENDPOINTS ---
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    phone = request.data.get('phone')
    role = request.data.get('role', 'client')
    username = request.data.get('name', f"user_{phone[-4:] if phone and len(phone)>=4 else 'new'}")

    if not phone:
        return Response({'error': 'Telefon raqam kiritilishi shart'}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(phone=phone, defaults={'username': username, 'role': role})
    if not created and role:
        user.role = role
        user.save()

    return Response({
        'message': 'SMS OTP kod yuborildi',
        'phone': phone,
        'test_otp': '123456',
        'is_new_user': created
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    phone = request.data.get('phone')
    otp = request.data.get('otp')

    if otp != '123456':
        return Response({'error': 'SMS-kod noto\'g\'ri'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(phone=phone)
        user.is_phone_verified = True
        user.save()
        
        if user.role == 'driver' and not hasattr(user, 'driver_profile'):
            Driver.objects.create(
                user=user,
                car_model='Cobalt',
                car_number='01 A 777 AA',
                car_color='Oq',
                license_number='AB1234567',
                status='approved',
                is_online=True,
                current_lat=41.311081,
                current_lng=69.240562
            )

        serializer = UserSerializer(user)
        return Response({
            'message': 'Muvaffaqiyatli tasdiqlandi',
            'token': f"mock-jwt-token-for-user-{user.id}",
            'user': serializer.data
        })
    except User.DoesNotExist:
        return Response({'error': 'Foydalanuvchi topilmadi'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    phone = request.data.get('phone')
    try:
        user = User.objects.get(phone=phone)
        serializer = UserSerializer(user)
        return Response({
            'token': f"mock-jwt-token-for-user-{user.id}",
            'user': serializer.data
        })
    except User.DoesNotExist:
        return Response({'error': 'Foydalanuvchi topilmadi'}, status=status.HTTP_404_NOT_FOUND)


# --- TARIFFS & ESTIMATION (WITH SURGE PRICING) ---
@api_view(['GET'])
@permission_classes([AllowAny])
def get_tariffs(request):
    tariffs = Tariff.objects.all()
    serializer = TariffSerializer(tariffs, many=True)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_tariff(request, pk):
    try:
        tariff = Tariff.objects.get(pk=pk)
        if 'base_price' in request.data:
            tariff.base_price = Decimal(str(request.data['base_price']))
        if 'price_per_km' in request.data:
            tariff.price_per_km = Decimal(str(request.data['price_per_km']))
        if 'price_per_minute' in request.data:
            tariff.price_per_minute = Decimal(str(request.data['price_per_minute']))
        if 'minimum_price' in request.data:
            tariff.minimum_price = Decimal(str(request.data['minimum_price']))
        tariff.save()
        return Response(TariffSerializer(tariff).data)
    except Tariff.DoesNotExist:
        return Response({'error': 'Tarif topilmadi'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def estimate_trip(request):
    pickup_lat = float(request.data.get('pickup_lat', 41.311081))
    pickup_lng = float(request.data.get('pickup_lng', 69.240562))
    dropoff_lat = float(request.data.get('dropoff_lat', 41.3275))
    dropoff_lng = float(request.data.get('dropoff_lng', 69.2817))

    distance_km = calculate_distance(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
    estimated_mins = max(3, int(distance_km * 2.5))

    current_hour = timezone.now().hour
    surge_multiplier = 1.0
    if 8 <= current_hour <= 10 or 17 <= current_hour <= 19:
        surge_multiplier = 1.35
    elif 23 <= current_hour or current_hour <= 5:
        surge_multiplier = 1.20

    tariffs = Tariff.objects.all()
    estimates = []
    for tariff in tariffs:
        calc_price = (float(tariff.base_price) + (distance_km * float(tariff.price_per_km)) + (estimated_mins * float(tariff.price_per_minute))) * surge_multiplier
        price = max(float(tariff.minimum_price), round(calc_price, -2))
        estimates.append({
            'tariff_id': tariff.id,
            'tariff_name': tariff.name,
            'icon': tariff.icon,
            'estimated_price': price,
            'distance_km': distance_km,
            'surge_multiplier': surge_multiplier,
            'estimated_duration_mins': estimated_mins
        })

    return Response({
        'distance_km': distance_km,
        'surge_multiplier': surge_multiplier,
        'estimated_duration_mins': estimated_mins,
        'estimates': estimates
    })


# --- PROMO CODE VALIDATION ---
@api_view(['POST'])
@permission_classes([AllowAny])
def validate_promo(request):
    code_str = request.data.get('code', '').strip().upper()
    try:
        promo = PromoCode.objects.get(code=code_str, is_active=True)
        return Response({
            'valid': True,
            'code': promo.code,
            'discount_amount': float(promo.discount_amount),
            'discount_percent': promo.discount_percent
        })
    except PromoCode.DoesNotExist:
        return Response({'valid': False, 'error': 'Promokod noto\'g\'ri yoki muddati o\'tgan'}, status=status.HTTP_400_BAD_REQUEST)


# --- TRIPS MANAGEMENT ---
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def trips_list_create(request):
    if request.method == 'GET':
        trips = Trip.objects.all().order_by('-id')
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        data = request.data
        client_phone = data.get('client_phone', '+998901234567')
        client, _ = User.objects.get_or_create(phone=client_phone, defaults={'username': f"Mijoz_{client_phone[-4:]}", 'role': 'client'})

        tariff_id = data.get('tariff_id')
        try:
            tariff = Tariff.objects.get(id=tariff_id)
        except Tariff.DoesNotExist:
            tariff = Tariff.objects.first()

        service_type = data.get('service_type', 'taxi')
        pickup_address = data.get('pickup_address', 'Toshkent sh., Amir Temur shoh ko\'chasi')
        pickup_lat = float(data.get('pickup_lat', 41.311081))
        pickup_lng = float(data.get('pickup_lng', 69.240562))
        dropoff_address = data.get('dropoff_address', 'Toshkent sh., Chilonzor tumani')
        dropoff_lat = float(data.get('dropoff_lat', 41.2825))
        dropoff_lng = float(data.get('dropoff_lng', 69.2045))

        distance_km = calculate_distance(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
        calc_price = float(tariff.base_price) + (distance_km * float(tariff.price_per_km))
        est_price = Decimal(str(max(float(tariff.minimum_price), round(calc_price, -2))))

        promo_obj = None
        discount = Decimal('0.00')
        promo_code_str = data.get('promo_code')
        if promo_code_str:
            try:
                promo_obj = PromoCode.objects.get(code=promo_code_str.upper(), is_active=True)
                if promo_obj.discount_amount > 0:
                    discount = promo_obj.discount_amount
                elif promo_obj.discount_percent > 0:
                    discount = est_price * Decimal(str(promo_obj.discount_percent / 100.0))
            except PromoCode.DoesNotExist:
                pass

        final_est_price = max(Decimal('0.00'), est_price - discount)

        trip = Trip.objects.create(
            client=client,
            tariff=tariff,
            service_type=service_type,
            pickup_address=pickup_address,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_address=dropoff_address,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            distance_km=Decimal(str(distance_km)),
            estimated_price=final_est_price,
            discount_applied=discount,
            promo_code=promo_obj,
            status='searching'
        )

        if service_type == 'delivery':
            Delivery.objects.create(
                trip=trip,
                package_size=data.get('package_size', 'small'),
                receiver_name=data.get('receiver_name', 'Qabul qiluvchi'),
                receiver_phone=data.get('receiver_phone', '+998909876543'),
                description=data.get('description', '')
            )

        payment_method = data.get('payment_method', 'cash')
        payment_provider = data.get('payment_provider', 'none')
        Payment.objects.create(
            trip=trip,
            method=payment_method,
            provider=payment_provider,
            amount=final_est_price,
            status='pending'
        )

        serializer = TripSerializer(trip)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def trip_detail(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
        serializer = TripSerializer(trip)
        return Response(serializer.data)
    except Trip.DoesNotExist:
        return Response({'error': 'Buyurtma topilmadi'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def cancel_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
        cancelled_by = request.data.get('by', 'client')
        trip.status = 'cancelled_by_client' if cancelled_by == 'client' else 'cancelled_by_driver'
        trip.save()
        serializer = TripSerializer(trip)
        return Response(serializer.data)
    except Trip.DoesNotExist:
        return Response({'error': 'Buyurtma topilmadi'}, status=status.HTTP_404_NOT_FOUND)


# --- DRIVER ENDPOINTS & WALLET TRANSACTIONS ---
@api_view(['GET'])
@permission_classes([AllowAny])
def available_trips(request):
    trips = Trip.objects.filter(status='searching').order_by('-id')
    serializer = TripSerializer(trips, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def accept_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
        if trip.status != 'searching':
            return Response({'error': 'Ushbu buyurtma allaqachon qabul qilingan'}, status=status.HTTP_400_BAD_REQUEST)

        driver_id = request.data.get('driver_id')
        if driver_id:
            driver = Driver.objects.get(id=driver_id)
        else:
            driver = Driver.objects.filter(is_online=True, status='approved').first()
            if not driver:
                driver = Driver.objects.first()

        if driver.balance < Decimal('10000.00') and trip.payment.method == 'cash':
            return Response({'error': 'Balansingiz yetarli emas (Minimal: 10,000 so\'m). Iltimos, hisobni to\'ldiring.'}, status=status.HTTP_400_BAD_REQUEST)

        trip.driver = driver
        trip.status = 'accepted'
        trip.save()

        serializer = TripSerializer(trip)
        return Response(serializer.data)
    except Trip.DoesNotExist:
        return Response({'error': 'Buyurtma topilmadi'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_trip_status(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
        new_status = request.data.get('status')

        trip.status = new_status
        if new_status == 'completed':
            trip.completed_at = timezone.now()
            trip.final_price = trip.estimated_price
            if hasattr(trip, 'payment'):
                trip.payment.status = 'paid'
                trip.payment.save()
            
            if trip.driver:
                commission_rate = Decimal('0.15')
                net_driver_earnings = trip.final_price * (Decimal('1.00') - commission_rate)
                
                driver = trip.driver
                driver.balance += net_driver_earnings
                driver.save()

                DriverTransaction.objects.create(
                    driver=driver,
                    amount=net_driver_earnings,
                    transaction_type='commission',
                    description=f"Safar #{trip.id} daromadi (15% komissiya yechildi)"
                )

        trip.save()
        serializer = TripSerializer(trip)
        return Response(serializer.data)
    except Trip.DoesNotExist:
        return Response({'error': 'Buyurtma topilmadi'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def driver_wallet(request):
    driver_id = request.query_params.get('driver_id', 1) or request.data.get('driver_id', 1)
    try:
        driver = Driver.objects.get(id=driver_id)
        if request.method == 'POST':
            amount = Decimal(str(request.data.get('amount', 50000)))
            driver.balance += amount
            driver.save()
            
            DriverTransaction.objects.create(
                driver=driver,
                amount=amount,
                transaction_type='deposit',
                description="Payme/Click orqali hisob to'ldirildi"
            )

        transactions = DriverTransaction.objects.filter(driver=driver).order_by('-id')
        return Response({
            'balance': float(driver.balance),
            'transactions': DriverTransactionSerializer(transactions, many=True).data
        })
    except Driver.DoesNotExist:
        return Response({'error': 'Haydovchi topilmadi'}, status=status.HTTP_404_NOT_FOUND)


# --- LIVE CHAT ENDPOINTS ---
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def chat_messages(request, trip_id):
    try:
        trip = Trip.objects.get(pk=trip_id)
        if request.method == 'GET':
            messages = ChatMessage.objects.filter(trip=trip).order_by('timestamp')
            return Response(ChatMessageSerializer(messages, many=True).data)
        elif request.method == 'POST':
            sender_id = request.data.get('sender_id', trip.client.id)
            sender = User.objects.get(id=sender_id)
            text = request.data.get('message', '')
            
            msg = ChatMessage.objects.create(trip=trip, sender=sender, message=text)
            return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)
    except Trip.DoesNotExist:
        return Response({'error': 'Buyurtma topilmadi'}, status=status.HTTP_404_NOT_FOUND)


# --- PAYMENTS & RATING ---
@api_view(['POST'])
@permission_classes([AllowAny])
def pay_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
        payment, _ = Payment.objects.get_or_create(trip=trip, defaults={'amount': trip.estimated_price, 'method': 'card'})
        payment.status = 'paid'
        payment.provider = request.data.get('provider', 'payme')
        payment.transaction_id = f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        payment.save()
        return Response({'message': 'To\'lov muvaffaqiyatli amalga oshirildi', 'payment': PaymentSerializer(payment).data})
    except Trip.DoesNotExist:
        return Response({'error': 'Buyurtma topilmadi'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def rate_trip(request, pk):
    try:
        trip = Trip.objects.get(pk=pk)
        rating_obj, _ = Rating.objects.get_or_create(trip=trip)

        client_rating = request.data.get('client_rating')
        comment = request.data.get('comment', '')
        if client_rating:
            rating_obj.client_rating_for_driver = int(client_rating)
            rating_obj.client_comment = comment
            rating_obj.save()

            if trip.driver:
                all_ratings = Rating.objects.filter(trip__driver=trip.driver, client_rating_for_driver__isnull=False)
                avg = sum([r.client_rating_for_driver for r in all_ratings]) / max(1, len(all_ratings))
                trip.driver.rating = round(avg, 2)
                trip.driver.save()

        return Response({'message': 'Rahmat! Baholaringiz saqlandi.', 'rating': RatingSerializer(rating_obj).data})
    except Trip.DoesNotExist:
        return Response({'error': 'Buyurtma topilmadi'}, status=status.HTTP_404_NOT_FOUND)


# --- ADMIN DASHBOARD & MANAGEMENT ---
@api_view(['GET'])
@permission_classes([AllowAny])
def admin_dashboard(request):
    total_trips = Trip.objects.count()
    completed_trips = Trip.objects.filter(status='completed').count()
    active_trips = Trip.objects.filter(status__in=['searching', 'accepted', 'arrived', 'in_progress']).count()
    total_drivers = Driver.objects.count()
    online_drivers = Driver.objects.filter(is_online=True).count()
    pending_drivers = Driver.objects.filter(status='pending').count()
    total_revenue = Payment.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0

    return Response({
        'total_trips': total_trips,
        'completed_trips': completed_trips,
        'active_trips': active_trips,
        'total_drivers': total_drivers,
        'online_drivers': online_drivers,
        'pending_drivers': pending_drivers,
        'total_revenue': float(total_revenue),
        'platform_commission': float(total_revenue) * 0.15
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def admin_drivers(request):
    if request.method == 'GET':
        drivers = Driver.objects.all().order_by('-id')
        serializer = DriverSerializer(drivers, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        driver_id = request.data.get('driver_id')
        action = request.data.get('action')
        try:
            driver = Driver.objects.get(id=driver_id)
            if action == 'approve':
                driver.status = 'approved'
            elif action == 'reject':
                driver.status = 'rejected'
            elif action == 'block':
                driver.status = 'blocked'
            driver.save()
            return Response(DriverSerializer(driver).data)
        except Driver.DoesNotExist:
            return Response({'error': 'Haydovchi topilmadi'}, status=status.HTTP_404_NOT_FOUND)
