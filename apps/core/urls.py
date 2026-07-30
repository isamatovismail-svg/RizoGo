from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.register, name='register'),
    path('auth/verify-otp/', views.verify_otp, name='verify-otp'),
    path('auth/login/', views.login_view, name='login'),

    # Tariffs & Estimator
    path('tariffs/', views.get_tariffs, name='tariffs'),
    path('admin/tariffs/<int:pk>/', views.update_tariff, name='update-tariff'),
    path('trips/estimate/', views.estimate_trip, name='estimate-trip'),

    # Promo Codes
    path('promos/validate/', views.validate_promo, name='validate-promo'),

    # Trips
    path('trips/', views.trips_list_create, name='trips-list-create'),
    path('trips/<int:pk>/', views.trip_detail, name='trip-detail'),
    path('trips/<int:pk>/cancel/', views.cancel_trip, name='cancel-trip'),
    path('trips/<int:pk>/rate/', views.rate_trip, name='rate-trip'),

    # Live Chat
    path('chat/<int:trip_id>/messages/', views.chat_messages, name='chat-messages'),

    # Driver & Wallet
    path('driver/available-trips/', views.available_trips, name='available-trips'),
    path('driver/trips/<int:pk>/accept/', views.accept_trip, name='accept-trip'),
    path('driver/trips/<int:pk>/status/', views.update_trip_status, name='update-trip-status'),
    path('driver/wallet/', views.driver_wallet, name='driver-wallet'),

    # Payments
    path('payments/<int:pk>/pay/', views.pay_trip, name='pay-trip'),

    # Admin
    path('admin/dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('admin/drivers/', views.admin_drivers, name='admin-drivers'),
]
