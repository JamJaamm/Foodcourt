import random
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import VerificationCode, Order, OrderItem, Address

def send_email(subject, template_name, context, recipient_list):
    html = render_to_string(template_name, context)
    plain = strip_tags(html)
    send_mail(subject, plain, settings.DEFAULT_FROM_EMAIL, recipient_list, html_message=html)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    email_val = ""

    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        email_val = email

        if not email or not password:
            error = "Both email and password are required."
        else:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if not user.is_active:
                    error = "Please verify your email before logging in."
                else:
                    login(request, user)
                    if not remember_me:
                        request.session.set_expiry(0)
                    else:
                        request.session.set_expiry(1209600)
                    return redirect('dashboard')
            else:
                error = "Invalid email or password."

    return render(request, 'login.html', {'error': error, 'email_val': email_val})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    form_data = {}

    if request.method == "POST":
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone
        }

        if not first_name or not last_name or not email or not password:
            error = "All fields except phone number are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        elif User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            error = "An account with this email already exists."
        else:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False
            )
            request.session['foodcourt_user_phone'] = phone

            code = f"{random.randint(100000, 999999)}"
            VerificationCode.objects.create(user=user, code=code)

            send_email(
                subject="Verify your FoodCourt account",
                template_name="emails/verify_email.html",
                context={"code": code},
                recipient_list=[email]
            )

            request.session['verification_user_id'] = user.id
            return redirect('verify')

    return render(request, 'register.html', {'error': error, 'form_data': form_data})

def verify_view(request):
    user_id = request.session.get('verification_user_id')
    if not user_id:
        return redirect('register')

    error = None
    success = None

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('register')

    if request.method == "POST":
        code = request.POST.get('code', '').strip()
        verification = VerificationCode.objects.filter(user=user, code=code, is_used=False).first()

        if not verification:
            error = "Invalid verification code."
        elif verification.is_expired():
            error = "Verification code has expired. Please register again."
            verification.delete()
        else:
            verification.is_used = True
            verification.save()
            user.is_active = True
            user.save()

            # Invalidate any old codes
            VerificationCode.objects.filter(user=user, is_used=False).delete()

            login(request, user)

            request.session.pop('verification_user_id', None)

            send_email(
                subject="Welcome to FoodCourt!",
                template_name="emails/welcome_email.html",
                context={
                    "name": user.first_name,
                    "dashboard_url": f"{request.scheme}://{request.get_host()}/dashboard/"
                },
                recipient_list=[user.email]
            )

            messages.success(request, f"Welcome to FoodCourt, {user.first_name}!")
            return redirect('dashboard')

    return render(request, 'verify.html', {'error': error, 'email': user.email})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required(login_url='login')
def place_order_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    items_data = data.get('items', [])
    delivery_address = data.get('delivery_address', '')
    payment_method = data.get('payment_method', 'cash')
    subtotal = float(data.get('subtotal', 0))
    delivery_fee = float(data.get('delivery_fee', 0))
    discount = float(data.get('discount', 0))
    total = float(data.get('total', 0))
    restaurant_name = data.get('restaurant_name', 'FoodCourt Order')

    if not items_data:
        return JsonResponse({'error': 'Cart is empty'}, status=400)
    if not delivery_address:
        return JsonResponse({'error': 'Delivery address required'}, status=400)

    year = datetime.now().year
    random_num = random.randint(1000, 9999)
    order_id = f'FC-{year}-{random_num}'

    order = Order.objects.create(
        user=request.user,
        order_id=order_id,
        restaurant_name=restaurant_name,
        delivery_address=delivery_address,
        payment_method=payment_method,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount=discount,
        total=total,
        status='confirmed'
    )

    for item in items_data:
        OrderItem.objects.create(
            order=order,
            name=item.get('name', 'Item'),
            price=float(item.get('price', 0)),
            quantity=int(item.get('qty', 1)),
            image=item.get('image', '')
        )

    return JsonResponse({
        'success': True,
        'order_id': order_id,
        'total': total
    })


@login_required(login_url='login')
def dashboard_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    orders_data = []
    total_spent = 0
    for o in orders:
        items = [{'name': i.name, 'qty': i.quantity, 'price': float(i.price)} for i in o.items.all()]
        total_spent += float(o.total)
        orders_data.append({
            'id': o.order_id,
            'restaurantName': o.restaurant_name,
            'restaurantImage': o.items.first().image if o.items.exists() and o.items.first().image else 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=100&q=80',
            'items': items,
            'subtotal': float(o.subtotal),
            'deliveryFee': float(o.delivery_fee),
            'discount': float(o.discount),
            'total': float(o.total),
            'status': o.status.capitalize(),
            'date': o.created_at.strftime('%Y-%m-%d'),
            'deliveryAddress': o.delivery_address,
            'paymentMethod': o.payment_method.title(),
        })

    stats = {
        'total_orders': orders.count(),
        'total_spent': round(total_spent, 2),
    }

    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    addresses_data = [{
        'id': a.id, 'label': a.label, 'address': a.full_address,
        'street': a.street, 'landmark': a.landmark,
        'city': a.city, 'state': a.state, 'country': a.country,
        'phone': a.phone, 'is_default': a.is_default
    } for a in addresses]
    return render(request, 'dashboard.html', {'user_orders': orders_data, 'stats': stats, 'user_addresses': addresses_data})

@login_required
def address_api(request):
    if request.method == 'GET':
        addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
        result = []
        for a in addresses:
            result.append({
                'id': a.id, 'label': a.label, 'address': a.full_address,
                'street': a.street, 'landmark': a.landmark,
                'city': a.city, 'state': a.state, 'country': a.country,
                'phone': a.phone, 'is_default': a.is_default
            })
        return JsonResponse({'addresses': result})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST

        action = data.get('action', 'create')

        if action == 'create':
            label = data.get('label', '').strip()
            street = data.get('street', '').strip()
            if not label or not street:
                return JsonResponse({'error': 'Label and street address are required'}, status=400)
            addr = Address.objects.create(
                user=request.user, label=label, street=street,
                landmark=data.get('landmark', '').strip(),
                city=data.get('city', '').strip(),
                state=data.get('state', '').strip(),
                country=data.get('country', '').strip(),
                phone=data.get('phone', '').strip()
            )
            return JsonResponse({'success': True, 'id': addr.id, 'address': addr.full_address, 'is_default': addr.is_default})

        elif action == 'update':
            try:
                addr = Address.objects.get(id=data.get('id'), user=request.user)
            except Address.DoesNotExist:
                return JsonResponse({'error': 'Address not found'}, status=404)
            if data.get('label'):
                addr.label = data['label'].strip()
            if data.get('street'):
                addr.street = data['street'].strip()
            if 'landmark' in data:
                addr.landmark = data['landmark'].strip()
            if 'city' in data:
                addr.city = data['city'].strip()
            if 'state' in data:
                addr.state = data['state'].strip()
            if 'country' in data:
                addr.country = data['country'].strip()
            if 'phone' in data:
                addr.phone = data['phone'].strip()
            addr.save()
            return JsonResponse({'success': True, 'id': addr.id, 'address': addr.full_address, 'is_default': addr.is_default})

        elif action == 'delete':
            try:
                addr = Address.objects.get(id=data.get('id'), user=request.user)
                addr.delete()
                return JsonResponse({'success': True})
            except Address.DoesNotExist:
                return JsonResponse({'error': 'Address not found'}, status=404)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def cart_view(request):
    addresses = []
    if request.user.is_authenticated:
        for a in Address.objects.filter(user=request.user).order_by('-is_default', '-created_at'):
            addresses.append({
                'id': a.id, 'label': a.label, 'address': a.full_address,
                'street': a.street, 'landmark': a.landmark,
                'city': a.city, 'state': a.state, 'country': a.country,
                'phone': a.phone, 'is_default': a.is_default
            })
    return render(request, 'cart.html', {'user_addresses_json': addresses})
