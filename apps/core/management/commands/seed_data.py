from django.core.management.base import BaseCommand
from apps.core.models import User, Driver, Tariff, Trip, Payment, PromoCode

class Command(BaseCommand):
    help = 'Seeds initial tariffs, promo codes, drivers, and test data for Rizo Go'

    def handle(self, *args, **options):
        self.stdout.write("Boshlang'ich ma'lumotlar yuklanmoqda...")

        # 1. Tariffs
        t_standart, _ = Tariff.objects.get_or_create(
            name='Standart',
            defaults={
                'base_price': 5000,
                'price_per_km': 1800,
                'price_per_minute': 400,
                'minimum_price': 8000,
                'icon': 'fa-taxi'
            }
        )

        t_komfort, _ = Tariff.objects.get_or_create(
            name='Komfort',
            defaults={
                'base_price': 8000,
                'price_per_km': 2500,
                'price_per_minute': 600,
                'minimum_price': 14000,
                'icon': 'fa-car-side'
            }
        )

        t_biznes, _ = Tariff.objects.get_or_create(
            name='Biznes',
            defaults={
                'base_price': 15000,
                'price_per_km': 4500,
                'price_per_minute': 1000,
                'minimum_price': 25000,
                'icon': 'fa-car'
            }
        )

        # 2. Promo Codes
        PromoCode.objects.get_or_create(
            code='RIZO2026',
            defaults={'discount_amount': 10000, 'discount_percent': 0, 'is_active': True}
        )
        PromoCode.objects.get_or_create(
            code='YANGI20',
            defaults={'discount_amount': 0, 'discount_percent': 20, 'is_active': True}
        )

        # 3. Super Admin User
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'phone': '+998900000000',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'is_phone_verified': True
            }
        )
        if not admin_user.check_password('admin123'):
            admin_user.set_password('admin123')
            admin_user.save()

        # 4. Test Drivers
        drivers_data = [
            {'name': 'anvar_driver', 'phone': '+998901112233', 'model': 'Chevrolet Cobalt', 'number': '01 A 777 AA', 'color': 'Oq', 'lat': 41.311081, 'lng': 69.240562, 'rating': 4.9},
            {'name': 'jasur_driver', 'phone': '+998902223344', 'model': 'Chevrolet Gentra', 'number': '01 B 888 BB', 'color': 'Qora', 'lat': 41.320000, 'lng': 69.255000, 'rating': 4.8},
            {'name': 'sardor_driver', 'phone': '+998903334455', 'model': 'BYD Song Plus', 'number': '01 C 999 CC', 'color': 'Kulrang', 'lat': 41.298000, 'lng': 69.220000, 'rating': 5.0},
        ]

        for d_info in drivers_data:
            u, _ = User.objects.get_or_create(
                username=d_info['name'],
                defaults={'phone': d_info['phone'], 'role': 'driver', 'is_phone_verified': True}
            )
            Driver.objects.get_or_create(
                user=u,
                defaults={
                    'car_model': d_info['model'],
                    'car_number': d_info['number'],
                    'car_color': d_info['color'],
                    'license_number': f"AB{u.id}98765",
                    'status': 'approved',
                    'is_online': True,
                    'current_lat': d_info['lat'],
                    'current_lng': d_info['lng'],
                    'rating': d_info['rating'],
                    'balance': 150000.00
                }
            )

        # 5. Test Client
        client_user, _ = User.objects.get_or_create(
            username='bekzod_client',
            defaults={'phone': '+998909998877', 'role': 'client', 'is_phone_verified': True}
        )

        self.stdout.write(self.style.SUCCESS("Muvaffaqiyatli: Boshlang'ich tariflar, promokodlar va test foydalanuvchilari yaratildi!"))
