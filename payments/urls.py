from django.urls import path

from . import views
from .webhooks import paystack_webhook

app_name = 'payments'

urlpatterns = [
    path('callback/', views.payment_callback, name='payments_callback'),
    path('retry/<str:order_id>/', views.payment_retry, name='payments_retry'),
    path('result/<str:order_id>/', views.payment_result, name='payments_result'),
    path('receipt/<str:order_id>/', views.payment_receipt, name='payments_receipt'),
    path('webhook/', paystack_webhook, name='payments_webhook'),
]
