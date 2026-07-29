from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from Foodcourt import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('restaurants/', TemplateView.as_view(template_name='restaurants.html'), name='restaurants'),
    path('restaurant/<int:pk>/', TemplateView.as_view(template_name='restaurant_detail.html'), name='restaurant_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('api/addresses/', views.address_api, name='address_api'),
    path('tracking/', TemplateView.as_view(template_name='order_tracking.html'), name='tracking'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify/', views.verify_view, name='verify'),
    path('order/place/', views.place_order_view, name='place_order'),
    path('logout/', views.logout_view, name='logout'),
]
