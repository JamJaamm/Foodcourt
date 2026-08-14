import random
import json
import functools
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.views.decorators.csrf import ensure_csrf_cookie
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.db import models as db_models
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
# from channels.generic.websocket import WebsocketConsumer
from .models import (
    VerificationCode, Order, OrderItem, Address,
    Restaurant, Category, MenuItem, InventoryItem, Coupon, Review, Profile,
    Riders, Delivery, DeliveryStatusLog, Notification, RiderReview
)
from .notifications import send_order_confirmation_emails
from . import delivery_services
from payments import services as payment_services
from payments.services import PaystackError
from payments.models import Payment

    


def send_email(subject, template_name, context, recipient_list):
    try:
        html = render_to_string(template_name, context)
        plain = strip_tags(html)
        send_mail(subject, plain, settings.DEFAULT_FROM_EMAIL, recipient_list, html_message=html)
        return True
    except Exception as e:
        print(f"[send_email] Failed to send '{subject}' to {recipient_list}: {e}")
        return False

def get_current_rider(request):
    rider_id = request.session.get('rider_id')
    if not rider_id:
        return None
    try:
        return Riders.objects.get(id=rider_id)
    except Riders.DoesNotExist:
        return None

def rider_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        rider = get_current_rider(request)
        if rider is None or rider.status != 'approved' or not rider.is_active:
            return redirect('rider_login')
        request.rider = rider
        return view_func(request, *args, **kwargs)
    return wrapper

def rider_public_payload(rider):
    return {
        'id': rider.id,
        'name': rider.get_full_name(),
        'first_name': rider.first_name,
        'last_name': rider.last_name,
        'phone': rider.phone,
        'vehicle': f"{rider.vehicle_brand} {rider.vehicle_model}".strip() or rider.vehicle_type,
        'vehicle_plate': rider.vehicle_plate,
        'avatar': rider.avatar_image.url if rider.avatar_image else rider.avatar,
        'rating': round(rider.reviews.aggregate(avg=db_models.Avg('rating'))['avg'] or 0, 1),
        'trips': rider.reviews.count(),
    }


def delivery_logs_payload(delivery):
    return [{
        'status': log.status,
        'label': log.label,
        'note': log.note,
        'created_at': log.created_at.isoformat(),
    } for log in delivery.status_logs.all()]


def safe_user_name(instance, fallback='Guest'):
    try:
        user = instance.user
    except ObjectDoesNotExist:
        return fallback
    if user is None:
        return fallback
    return user.get_full_name() or user.email or user.username or fallback


def delivery_payload(delivery, include_otp=False):
    if delivery is None:
        return None
    rider = delivery.rider
    return {
        'id': delivery.id,
        'status': delivery.status,
        'status_label': delivery.status_label,
        'order_id': delivery.order.order_id,
        'restaurant': delivery.order.restaurant_name,
        'payout': float(delivery.payout),
        'otp': delivery.otp if include_otp else None,
        'otp_attempts': delivery.otp_attempts,
        'rider': rider_public_payload(rider) if rider else None,
        'logs': delivery_logs_payload(delivery),
        'created_at': delivery.created_at.isoformat(),
        'updated_at': delivery.updated_at.isoformat(),
    }


def _parse_decimal(value):
    if value is None or str(value).strip() == '':
        return None
    try:
        d = Decimal(str(value))
        return d if d.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None

def _parse_int(value, default=0):
    if value is None or str(value).strip() == '':
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default

def login_view(request):
    if request.user.is_authenticated:
        return get_dashboard_redirect(request.user)

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
            if user is None:
                try:
                    user_obj = User.objects.get(email=email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            if user is not None:
                if not user.is_active:
                    error = "Please verify your email before logging in."
                else:
                    login(request, user)
                    if not remember_me:
                        request.session.set_expiry(0)
                    else:
                        request.session.set_expiry(1209600)
                    return get_dashboard_redirect(user)
            else:
                error = "Invalid email or password."

    return render(request, 'login.html', {'error': error, 'email_val': email_val})

def register_view(request):
    if request.user.is_authenticated:
        return get_dashboard_redirect(request.user)

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

            email_sent = send_email(
                subject="Verify your FoodCourt account",
                template_name="emails/verify_email.html",
                context={"code": code},
                recipient_list=[email]
            )

            request.session['verification_user_id'] = user.id
            request.session['verification_email_sent'] = email_sent
            return redirect('verify')

    return render(request, 'register.html', {'error': error, 'form_data': form_data})

def restaurant_register_view(request):
    if request.user.is_authenticated:
        return get_dashboard_redirect(request.user)

    error = None
    form_data = {}

    if request.method == "POST":
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        rest_name = request.POST.get('restaurant_name', '').strip()
        cuisine = request.POST.get('cuisine', '').strip()
        address = request.POST.get('address', '').strip()
        rest_phone = request.POST.get('restaurant_phone', '').strip()
        rest_email = request.POST.get('restaurant_email', '').strip()

        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'restaurant_name': rest_name,
            'cuisine': cuisine,
            'address': address,
            'restaurant_phone': rest_phone,
            'restaurant_email': rest_email,
        }

        if not first_name or not last_name or not email or not password or not rest_name:
            error = "All fields except optional restaurant details are required."
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

            Restaurant.objects.create(
                owner=user,
                name=rest_name,
                cuisine=cuisine,
                address=address,
                phone=rest_phone or phone,
                email=rest_email or email,
            )

            code = f"{random.randint(100000, 999999)}"
            VerificationCode.objects.create(user=user, code=code)

            email_sent = send_email(
                subject="Verify your FoodCourt restaurant account",
                template_name="emails/verify_email.html",
                context={"code": code},
                recipient_list=[email]
            )

            request.session['verification_user_id'] = user.id
            request.session['verification_email_sent'] = email_sent
            return redirect('verify')

    return render(request, 'restaurant_register.html', {'error': error, 'form_data': form_data})

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
            return get_dashboard_redirect(user)

    email_sent = request.session.get('verification_email_sent', True)
    dev_code = None
    if not email_sent and settings.DEBUG:
        latest = VerificationCode.objects.filter(user=user, is_used=False).first()
        dev_code = latest.code if latest else None

    return render(request, 'verify.html', {
        'error': error,
        'email': user.email,
        'email_sent': email_sent,
        'dev_code': dev_code,
    })

def logout_view(request):
    logout(request)
    return redirect('home')

def forgot_password_view(request):
    if request.user.is_authenticated:
        return get_dashboard_redirect(request.user)

    error = None
    email_val = ""

    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        email_val = email

        if not email:
            error = "Please enter your email address."
        else:
            user = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
            reset_link = None
            email_sent = False
            if user is not None and user.is_active:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_link = f"{settings.SITE_URL.rstrip('/')}{reverse('reset_password_confirm', args=[uid, token])}"
                email_sent = send_email(
                    subject="Reset your FoodCourt password",
                    template_name="emails/password_reset_email.html",
                    context={"user": user, "reset_link": reset_link},
                    recipient_list=[user.email]
                )
            request.session['reset_email_sent'] = email_sent
            request.session['reset_dev_link'] = reset_link if (not email_sent and settings.DEBUG) else None
            return redirect('reset_password_done')

    return render(request, 'forgot_password.html', {'error': error, 'email_val': email_val})

def reset_password_done_view(request):
    email_sent = request.session.get('reset_email_sent', True)
    dev_link = request.session.get('reset_dev_link', None)
    return render(request, 'reset_password_done.html', {
        'email_sent': email_sent,
        'dev_link': dev_link,
    })

def reset_password_view(request, uidb64, token):
    user = None
    valid = False
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        valid = default_token_generator.check_token(user, token)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        valid = False

    if not valid:
        return render(request, 'reset_password.html', {'invalid': True})

    error = None
    if request.method == "POST":
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if not password or len(password) < 6:
            error = "Password must be at least 6 characters long."
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            user.set_password(password)
            user.save()
            messages.success(request, "Your password has been reset. Please sign in with your new password.")
            return redirect('login')

    return render(request, 'reset_password.html', {'user': user, 'error': error, 'valid': True})

def is_restaurant_admin(user):
    if not user.is_authenticated:
        return False
    return Restaurant.objects.filter(owner=user).exists()

def is_platform_admin(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.is_staff

def get_dashboard_redirect(user):
    if is_restaurant_admin(user):
        return redirect('restaurant_dashboard')
    if is_platform_admin(user):
        return redirect('admin_dashboard')
    return redirect('dashboard')

def auth_context_processor(request):
    user = request.user
    if user.is_authenticated and is_restaurant_admin(user):
        dashboard_url = '/restaurant-admin/'
    elif user.is_authenticated and is_platform_admin(user):
        dashboard_url = '/admin-dashboard/'
    else:
        dashboard_url = '/dashboard/'
    return {
        'is_admin_user': user.is_authenticated and (is_restaurant_admin(user) or is_platform_admin(user)),
        'dashboard_url': dashboard_url,
    }

CATEGORY_KEYWORDS = {
    'pizza': ['pizza', 'italian'],
    'burgers': ['burger', 'american', 'grill'],
    'sushi': ['sushi', 'japanese', 'asian'],
    'tacos': ['taco', 'mexican'],
    'ramen': ['ramen', 'noodle'],
    'salads': ['salad', 'healthy', 'vegan', 'vegetarian'],
    'desserts': ['dessert', 'cake', 'bakery', 'sweet'],
    'wings': ['wing', 'fried', 'chicken'],
}

def guess_category(cuisine):
    c = (cuisine or '').lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in c for w in words):
            return cat
    return 'other'

def build_restaurants_payload():
    default_img = 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80'
    db_restaurants = []
    for r in Restaurant.objects.all():
        db_restaurants.append({
            'id': r.id,
            'name': r.name,
            'description': r.description or '',
            'category': guess_category(r.cuisine),
            'tags': [r.cuisine] if r.cuisine else [],
            'rating': float(r.rating or 0),
            'reviewCount': r.reviews.count(),
            'deliveryTime': 25,
            'deliveryFee': float(r.delivery_fee),
            'minOrder': float(r.min_order),
            'image': r.cover_image or r.logo or default_img,
            'isOpen': r.is_open,
            'isFeatured': False,
            'isNew': True,
            'isFavorite': False,
            'cuisine': r.cuisine or 'Food Court',
            'address': r.address or '',
            'distance': 1.0,
        })
    return db_restaurants

def home_view(request):
    return render(request, 'index.html', {'db_restaurants': build_restaurants_payload()})

def rider_view(request):
    return render(request, 'Riders/rider.html')


def rider_banks_api(request):
    """Return the list of Nigerian banks from Paystack for the rider form."""
    try:
        banks = payment_services.list_banks('NGN')
    except PaystackError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=502)
    return JsonResponse({'ok': True, 'banks': banks})


def rider_bank_resolve_api(request):
    """Resolve an account name for a rider's bank + account number."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)

    try:
        data = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid request.'}, status=400)

    bank_code = str(data.get('bank_code', '') or '').strip()
    account_number = str(data.get('account_number', '') or '').strip()

    if not bank_code:
        return JsonResponse({'ok': False, 'error': 'Please select a bank.'}, status=400)
    if not account_number.isdigit() or len(account_number) != 10:
        return JsonResponse({'ok': False, 'error': 'Enter a valid 10-digit account number.'}, status=400)

    try:
        account_name = payment_services.resolve_bank_account(bank_code, account_number)
    except PaystackError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=422)

    return JsonResponse({'ok': True, 'account_number': account_number, 'account_name': account_name})

def rider_login_view(request):
    if get_current_rider(request):
        return redirect('rider_dashboard')

    error = None
    email_val = ""

    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        email_val = email

        try:
            rider = Riders.objects.get(email=email)
        except Riders.DoesNotExist:
            rider = None

        if rider is None or not rider.check_password(password):
            error = "Invalid email or password."
        elif rider.status == 'pending':
            error = "Please verify your email before logging in."
        elif rider.status == 'verified':
            error = "Your application is awaiting admin approval. You'll receive an email once you're approved."
        elif rider.status == 'rejected':
            error = "Your rider application was rejected."
        elif not rider.is_active:
            error = "Your rider account is not active yet."
        else:
            request.session['rider_id'] = rider.id
            rider.last_login = timezone.now()
            rider.save(update_fields=['last_login'])
            return redirect('rider_dashboard')

    return render(request, 'Riders/rider_login.html', {'error': error, 'email_val': email_val})

def rider_register_view(request):
    if request.method != "POST":
        return redirect('riders')

    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}
    else:
        data = request.POST

    def val(key):
        return str(data.get(key, '') or '').strip()

    first_name = val('first_name')
    last_name = val('last_name')
    email = val('email').lower()
    phone = val('phone')
    password = str(data.get('password', '') or '')
    dob_raw = val('dob')

    errors = {}
    if not first_name:
        errors['first_name'] = 'First name is required.'
    if not last_name:
        errors['last_name'] = 'Last name is required.'
    if not email:
        errors['email'] = 'Email is required.'
    elif Riders.objects.filter(email=email).exists():
        errors['email'] = 'An account with this email already exists.'
    if not phone:
        errors['phone'] = 'Phone number is required.'
    if len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'

    dob = None
    if dob_raw:
        try:
            dob = datetime.strptime(dob_raw, '%Y-%m-%d').date()
        except ValueError:
            dob = None
    if not dob:
        errors['dob'] = 'A valid date of birth is required.'

    avatar_file = request.FILES.get('avatar_file')
    if avatar_file:
        if not avatar_file.content_type.startswith('image/'):
            errors['avatar'] = 'Profile picture must be an image.'
        elif avatar_file.size > 5 * 1024 * 1024:
            errors['avatar'] = 'Profile picture is too large (max 5MB).'
    else:
        errors['avatar'] = 'Please upload a profile picture.'

    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    rider = Riders(
        username=email,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        dob=dob,
        avatar=val('avatar'),
        avatar_image=avatar_file,
        address=val('address'),
        city=val('city'),
        state=val('state'),
        country=val('country'),
        postal_code=val('postal_code'),
        vehicle_type=val('vehicle_type'),
        vehicle_brand=val('vehicle_brand'),
        vehicle_model=val('vehicle_model'),
        vehicle_color=val('vehicle_color'),
        vehicle_plate=val('vehicle_plate'),
        bank_name=val('bank_name'),
        account_name=val('account_name'),
        account_number=val('account_number'),
        documents=val('documents'),
        status='pending',
        is_active=False,
    )
    rider.set_password(password)
    rider.save()

    code = f"{random.randint(100000, 999999)}"
    VerificationCode.objects.create(rider=rider, code=code)

    email_sent = send_email(
        subject="Verify your FoodCourt rider account",
        template_name="emails/rider_verify_email.html",
        context={"code": code, "name": first_name},
        recipient_list=[email],
    )

    request.session['rider_verification_rider_id'] = rider.id
    request.session['rider_verification_email_sent'] = email_sent

    verify_url = reverse('rider_verify')
    return JsonResponse({'ok': True, 'redirect': verify_url, 'email_sent': email_sent})

def rider_verify_view(request):
    rider_id = request.session.get('rider_verification_rider_id')
    if not rider_id:
        return redirect('riders')

    try:
        rider = Riders.objects.get(id=rider_id)
    except Riders.DoesNotExist:
        return redirect('riders')

    error = None
    success = None

    if request.method == "POST":
        code = request.POST.get('code', '').strip()
        verification = VerificationCode.objects.filter(rider=rider, code=code, is_used=False).first()

        if not verification:
            error = "Invalid verification code."
        elif verification.is_expired():
            error = "Verification code has expired. Please apply again."
            verification.delete()
        else:
            verification.is_used = True
            verification.save()
            rider.status = 'verified'
            rider.save(update_fields=['status'])

            VerificationCode.objects.filter(rider=rider, is_used=False).delete()

            request.session.pop('rider_verification_rider_id', None)
            request.session.pop('rider_verification_email_sent', None)

            send_email(
                subject="Welcome to FoodCourt Riders!",
                template_name="emails/rider_welcome_email.html",
                context={
                    "name": rider.first_name,
                    "login_url": f"{request.scheme}://{request.get_host()}{reverse('rider_login')}",
                },
                recipient_list=[rider.email],
            )

            success = "Your email has been verified. Your application is now with our team — you'll receive an email once an admin approves your account, then you can log in."

    email_sent = request.session.get('rider_verification_email_sent', True)
    dev_code = None
    if not email_sent and settings.DEBUG:
        latest = VerificationCode.objects.filter(rider=rider, is_used=False).first()
        dev_code = latest.code if latest else None

    return render(request, 'Riders/rider_verify.html', {
        'error': error,
        'success': success,
        'email': rider.email,
        'dev_code': dev_code,
    })

@rider_required
def rider_dashboard_view(request):
    rider = request.rider

    available = Delivery.objects.filter(status='searching').exclude(declined_by=rider).select_related('order').order_by('-created_at')
    active = Delivery.objects.filter(rider=rider, status__in=Delivery.ACTIVE_STATUSES).select_related('order').first()
    history = Delivery.objects.filter(rider=rider, status__in=['delivered', 'cancelled']).select_related('order').order_by('-updated_at')

    delivered = Delivery.objects.filter(rider=rider, status='delivered')
    earned = sum(float(d.payout) for d in delivered)

    stats = {
        'active': 1 if active else 0,
        'available': available.count(),
        'delivered': delivered.count(),
        'earned': earned,
    }

    return render(request, 'Riders/rider_dashboard.html', {
        'rider': rider,
        'available_requests': available,
        'active_delivery': active,
        'delivery_history': history,
        'rider_stats': stats,
    })

@rider_required
def rider_profile_update_view(request):
    rider = request.rider
    if request.method == 'POST':
        if 'avatar_file' in request.FILES:
            f = request.FILES['avatar_file']
            if not f.content_type.startswith('image/'):
                messages.error(request, "Profile picture must be an image.")
                return redirect('rider_dashboard')
            if f.size > 5 * 1024 * 1024:
                messages.error(request, "Profile picture is too large (max 5MB).")
                return redirect('rider_dashboard')
            if rider.avatar_image:
                rider.avatar_image.delete(save=False)
            rider.avatar_image = f

        rider.first_name = request.POST.get('first_name', '').strip() or rider.first_name
        rider.last_name = request.POST.get('last_name', '').strip() or rider.last_name
        rider.phone = request.POST.get('phone', '').strip() or rider.phone
        rider.gender = request.POST.get('gender', '').strip()
        dob_raw = request.POST.get('dob', '').strip()
        if dob_raw:
            try:
                rider.dob = datetime.strptime(dob_raw, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Invalid date of birth.")
                return redirect('rider_dashboard')
        rider.address = request.POST.get('address', '').strip()
        rider.city = request.POST.get('city', '').strip()
        rider.state = request.POST.get('state', '').strip()
        rider.country = request.POST.get('country', '').strip()
        rider.postal_code = request.POST.get('postal_code', '').strip()
        rider.vehicle_type = request.POST.get('vehicle_type', '').strip()
        rider.vehicle_brand = request.POST.get('vehicle_brand', '').strip()
        rider.vehicle_model = request.POST.get('vehicle_model', '').strip()
        rider.vehicle_color = request.POST.get('vehicle_color', '').strip()
        rider.vehicle_plate = request.POST.get('vehicle_plate', '').strip()
        rider.bank_name = request.POST.get('bank_name', '').strip()
        rider.account_name = request.POST.get('account_name', '').strip()
        rider.account_number = request.POST.get('account_number', '').strip()
        rider.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('rider_dashboard')
    return redirect('rider_dashboard')

@rider_required
def rider_toggle_online_view(request):
    rider = request.rider
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'online':
            if not rider.is_available:
                messages.error(request, "You can't go online while on an active delivery.")
            else:
                rider.is_online = True
        elif action == 'offline':
            rider.is_online = False
        rider.save(update_fields=['is_online'])
    return redirect('rider_dashboard')

@rider_required
def rider_accept_delivery_view(request, delivery_id):
    rider = request.rider
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id)
        ok, error = delivery_services.accept_delivery(delivery, rider)
        if ok:
            messages.success(request, "Delivery accepted. Head to the restaurant!")
        else:
            messages.error(request, error)
    return redirect('rider_dashboard')

@rider_required
def rider_decline_delivery_view(request, delivery_id):
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id)
        delivery_services.decline_delivery(delivery, request.rider)
    return redirect('rider_dashboard')

@rider_required
def rider_delivery_status_view(request, delivery_id):
    rider = request.rider
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id, rider=rider)
        next_status = request.POST.get('status', '')
        ok, error = delivery_services.advance_delivery_status(delivery, rider, next_status)
        if ok:
            messages.success(request, "Delivery status updated.")
        else:
            messages.error(request, error)
    return redirect('rider_dashboard')

@rider_required
def rider_complete_delivery_view(request, delivery_id):
    rider = request.rider
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id, rider=rider)
        otp = request.POST.get('otp', '')
        ok, error = delivery_services.complete_delivery(delivery, rider, otp)
        if ok:
            messages.success(request, "Delivery completed! You're now available for new orders.")
        else:
            messages.error(request, error)
    return redirect('rider_dashboard')

@rider_required
def rider_deliveries_api(request):
    rider = request.rider
    available = [{
        'id': d.id,
        'order_id': d.order.order_id,
        'restaurant': d.order.restaurant_name,
        'address': d.order.delivery_address,
        'payment': d.order.payment_method,
        'items': d.order.items.count(),
        'total': float(d.order.total),
        'payout': float(d.payout or d.order.delivery_fee or 0),
        'created_at': d.created_at.strftime('%b %d, %I:%M %p'),
    } for d in Delivery.objects.filter(status='searching').exclude(declined_by=rider).select_related('order').order_by('-created_at')]

    active = Delivery.objects.filter(rider=rider, status__in=Delivery.ACTIVE_STATUSES).select_related('order').first()
    active_data = delivery_payload(active) if active else None

    return JsonResponse({
        'is_online': rider.is_online,
        'is_available': rider.is_available,
        'available': available,
        'active': active_data,
    })

def rider_logout_view(request):
    request.session.pop('rider_id', None)
    return redirect('rider_login')

def restaurants_view(request):
    return render(request, 'restaurants.html', {'db_restaurants': build_restaurants_payload()})

def restaurant_detail_view(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    default_img = 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80'
    default_avatar = 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&q=80'

    restaurant_json = {
        'id': restaurant.id,
        'name': restaurant.name,
        'description': restaurant.description or '',
        'category': guess_category(restaurant.cuisine),
        'tags': [restaurant.cuisine] if restaurant.cuisine else [],
        'rating': float(restaurant.rating or 0),
        'reviewCount': restaurant.reviews.count(),
        'deliveryTime': 25,
        'deliveryFee': float(restaurant.delivery_fee),
        'minOrder': float(restaurant.min_order),
        'image': restaurant.cover_image or restaurant.logo or default_img,
        'isOpen': restaurant.is_open,
        'isFeatured': False,
        'isNew': False,
        'cuisine': restaurant.cuisine or 'Food Court',
        'address': restaurant.address or '',
    }

    menu_json = [{
        'id': item.id,
        'restaurantId': restaurant.id,
        'name': item.name,
        'description': item.description,
        'price': float(item.price),
        'category': item.category.name if item.category else 'Other',
        'image': item.image.url if item.image else '',
        'isPopular': item.is_popular,
        'isVeg': item.is_veg,
        'calories': item.calories,
        'prepTime': item.prep_time,
    } for item in MenuItem.objects.filter(restaurant=restaurant, is_available=True).order_by('name')]

    reviews_json = [{
        'id': r.id,
        'name': safe_user_name(r, 'Anonymous'),
        'avatar': default_avatar,
        'rating': r.rating,
        'text': r.comment,
        'date': r.created_at.strftime('%b %d, %Y'),
        'location': 'Verified Customer',
        'reply': r.reply,
    } for r in restaurant.reviews.filter(is_hidden=False).order_by('-created_at')]

    return render(request, 'restaurant_detail.html', {
        'restaurant': restaurant,
        'restaurant_json': restaurant_json,
        'menu_json': menu_json,
        'reviews_json': reviews_json,
        'has_menu': len(menu_json) > 0,
    })

@login_required(login_url='login')
def submit_review_view(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    restaurant = get_object_or_404(Restaurant, pk=pk)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except json.JSONDecodeError:
        data = request.POST

    try:
        rating = int(data.get('rating', 0))
    except (TypeError, ValueError):
        rating = 0
    comment = (data.get('comment') or '').strip()

    if rating < 1 or rating > 5:
        return JsonResponse({'error': 'Please select a star rating between 1 and 5.'}, status=400)

    Review.objects.update_or_create(
        restaurant=restaurant,
        user=request.user,
        defaults={'rating': rating, 'comment': comment, 'is_hidden': False},
    )

    reviews_qs = restaurant.reviews.filter(is_hidden=False).order_by('-created_at')
    avg = (sum(float(r.rating) for r in reviews_qs) / len(reviews_qs)) if reviews_qs else float(rating)
    default_avatar = 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&q=80'
    reviews = [{
        'id': r.id,
        'name': safe_user_name(r, 'Anonymous'),
        'avatar': default_avatar,
        'rating': r.rating,
        'text': r.comment,
        'date': r.created_at.strftime('%b %d, %Y'),
        'location': 'Verified Customer',
        'reply': r.reply,
    } for r in reviews_qs]

    return JsonResponse({
        'success': True,
        'rating': round(avg, 1),
        'reviewCount': reviews_qs.count(),
        'reviews': reviews,
    })

def build_platform_stats():
    total_revenue = Order.objects.exclude(status='cancelled').aggregate(total=db_models.Sum('total'))['total'] or 0
    return {
        'pending_riders': Riders.objects.filter(status='verified').count(),
        'new_riders': Riders.objects.filter(status='pending').count(),
        'total_riders': Riders.objects.filter(status='approved').count(),
        'restaurants': Restaurant.objects.count(),
        'users': User.objects.count(),
        'orders': Order.objects.count(),
        'total_revenue': float(total_revenue),
        'delivered_orders': Order.objects.filter(status='delivered').count(),
    }

@login_required(login_url='login')
def admin_dashboard_view(request, section=None):
    is_staff = request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

    # ── Rider management section ──
    if section == 'riders':
        if not is_staff:
            return redirect('admin_dashboard')
        riders = Riders.objects.order_by('-created_at')
        status_filter = request.GET.get('status', '').strip()
        if status_filter:
            riders = riders.filter(status=status_filter)
        return render(request, 'admin_dashboard.html', {
            'section': 'riders',
            'riders': riders,
            'rider_status_filter': status_filter,
            'platform_stats': build_platform_stats(),
            'hide_navbar': True,
        })

    # ── Registered restaurants section ──
    if section == 'restaurants':
        if not is_staff:
            return redirect('admin_dashboard')
        registered_restaurants = Restaurant.objects.select_related('owner').order_by('-created_at')
        restaurant_query = request.GET.get('q', '').strip()
        if restaurant_query:
            registered_restaurants = registered_restaurants.filter(
                db_models.Q(name__icontains=restaurant_query) | db_models.Q(owner__email__icontains=restaurant_query)
            )
        restaurant_rows = []
        for r in registered_restaurants:
            restaurant_rows.append({
                'id': r.id,
                'name': r.name,
                'cuisine': r.cuisine or '—',
                'phone': r.phone or '—',
                'email': r.email or '—',
                'address': r.address or '—',
                'owner': r.owner.get_full_name() or r.owner.username,
                'owner_email': r.owner.email,
                'rating': float(r.rating or 0),
                'is_open': r.is_open,
                'orders': r.orders.count(),
                'menu_items': r.menu_items.count(),
                'created_at': r.created_at,
            })
        return render(request, 'admin_dashboard.html', {
            'section': 'restaurants',
            'restaurant_rows': restaurant_rows,
            'restaurant_query': restaurant_query,
            'platform_stats': build_platform_stats(),
            'hide_navbar': True,
        })

    # ── Platform orders section ──
    if section == 'orders':
        if not is_staff:
            return redirect('admin_dashboard')
        orders = Order.objects.select_related('user', 'restaurant').order_by('-created_at')
        order_status_filter = request.GET.get('status', '').strip()
        if order_status_filter:
            orders = orders.filter(status=order_status_filter)
        return render(request, 'admin_dashboard.html', {
            'section': 'orders',
            'orders': orders,
            'order_status_filter': order_status_filter,
            'platform_stats': build_platform_stats(),
            'hide_navbar': True,
        })

    # ── Payment transactions section ──
    if section == 'payments':
        if not is_staff:
            return redirect('admin_dashboard')
        payments_qs = Payment.objects.select_related('order', 'customer').order_by('-created_at')
        payment_status_filter = request.GET.get('status', '').strip()
        payment_query = request.GET.get('q', '').strip()
        if payment_status_filter:
            payments_qs = payments_qs.filter(status=payment_status_filter)
        if payment_query:
            payments_qs = payments_qs.filter(
                db_models.Q(transaction_reference__icontains=payment_query)
                | db_models.Q(paystack_reference__icontains=payment_query)
                | db_models.Q(order__order_id__icontains=payment_query)
                | db_models.Q(customer__email__icontains=payment_query)
            )
        return render(request, 'admin_dashboard.html', {
            'section': 'payments',
            'payments': payments_qs[:200],
            'payment_status_filter': payment_status_filter,
            'payment_query': payment_query,
            'platform_stats': build_platform_stats(),
            'hide_navbar': True,
        })

    try:
        restaurant = Restaurant.objects.get(owner=request.user)
    except Restaurant.DoesNotExist:
        restaurant = None

    if restaurant is None:
        pending_approvals = []
        if is_staff:
            pending_approvals = Riders.objects.filter(status='verified').order_by('-created_at')[:8]
        return render(request, 'admin_dashboard.html', {
            'no_restaurant': True,
            'restaurant': None,
            'hide_navbar': True,
            'platform_stats': build_platform_stats() if is_staff else None,
            'platform_orders': Order.objects.order_by('-created_at')[:8],
            'pending_approvals': pending_approvals,
        })

    orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')
    today = timezone.localdate()
    today_orders = orders.filter(created_at__date=today)
    today_revenue = sum(float(o.total) for o in today_orders)
    avg_rating = restaurant.reviews.aggregate(avg=db_models.Avg('rating'))['avg']

    stats = {
        'today_revenue': today_revenue,
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'completed_orders': orders.filter(status='delivered').count(),
        'customers': orders.values('user').distinct().count(),
        'menu_items': restaurant.menu_items.count(),
        'low_stock': restaurant.inventory.filter(stock__lte=db_models.F('low_stock_threshold')).count(),
        'review_count': restaurant.reviews.count(),
        'avg_rating': round(float(avg_rating), 1) if avg_rating else 0,
    }

    pending_approvals = []
    if is_staff:
        pending_approvals = Riders.objects.filter(status='verified').order_by('-created_at')[:8]

    return render(request, 'admin_dashboard.html', {
        'restaurant': restaurant,
        'stats': stats,
        'orders': orders,
        'hide_navbar': True,
        'platform_stats': build_platform_stats() if is_staff else None,
        'pending_approvals': pending_approvals,
    })

@login_required(login_url='login')
def approve_rider_view(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')
    rider = get_object_or_404(Riders, pk=pk)
    if rider.status != 'rejected':
        rider.status = 'approved'
        rider.is_active = True
        rider.save(update_fields=['status', 'is_active'])
        send_email(
            subject="You're approved — Welcome to FoodCourt Riders!",
            template_name="emails/rider_approved_email.html",
            context={
                "name": rider.first_name,
                "login_url": f"{request.scheme}://{request.get_host()}{reverse('rider_login')}",
            },
            recipient_list=[rider.email],
        )
        messages.success(request, f"{rider.first_name} {rider.last_name} approved. A login email was sent.")
    return redirect('admin_riders')

@login_required(login_url='login')
def reject_rider_view(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')
    rider = get_object_or_404(Riders, pk=pk)
    if rider.status != 'rejected':
        rider.status = 'rejected'
        rider.is_active = False
        rider.save(update_fields=['status', 'is_active'])
        send_email(
            subject="Update on your FoodCourt rider application",
            template_name="emails/rider_rejected_email.html",
            context={
                "name": rider.first_name,
            },
            recipient_list=[rider.email],
        )
        messages.success(request, f"{rider.first_name} {rider.last_name}'s application was rejected.")
    return redirect('admin_riders')

@login_required(login_url='login')
def tracking_view(request, order_id=None):
    order_data = None

    if not order_id:
        active_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery']
        recent = Order.objects.filter(
            user=request.user,
            status__in=active_statuses,
        ).order_by('-created_at').first()
        if recent:
            return redirect('tracking_detail', order_id=recent.order_id)

    if order_id:
        try:
            order = Order.objects.get(order_id=order_id, user=request.user)
            order_data = build_order_data(order)
        except Order.DoesNotExist:
            pass
    past_orders = Order.objects.filter(
        user=request.user,
        status__in=['delivered', 'cancelled'],
    ).order_by('-created_at')[:15]
    return render(request, 'order_tracking.html', {
        'order_data': order_data,
        'tracking_order_id': order_id,
        'past_orders': past_orders,
    })

@login_required(login_url='login')
def order_delivery_api(request, order_id):
    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    return JsonResponse(build_order_data(order))

def build_order_data(order, include_otp=True):
    items = [{
        'name': i.name, 'qty': i.quantity,
        'price': float(i.price), 'image': i.image,
    } for i in order.items.all()]
    delivery = getattr(order, 'delivery', None)
    review = delivery.review if delivery and hasattr(delivery, 'review') else None
    return {
        'id': order.order_id,
        'restaurant': order.restaurant_name,
        'items': items,
        'subtotal': float(order.subtotal),
        'delivery_fee': float(order.delivery_fee),
        'discount': float(order.discount),
        'total': float(order.total),
        'status': order.status,
        'payment_status': order.payment_status,
        'address': order.delivery_address,
        'payment': order.payment_method,
        'date': order.created_at.isoformat(),
        'delivery': delivery_payload(delivery, include_otp=include_otp),
        'can_rate': order.status == 'delivered' and review is None and delivery is not None and delivery.rider is not None,
    }

@login_required(login_url='login')
def rate_rider_api(request, order_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

    delivery = getattr(order, 'delivery', None)
    if delivery is None or delivery.rider is None:
        return JsonResponse({'error': 'No rider assigned to this order'}, status=400)
    if delivery.status != 'delivered':
        return JsonResponse({'error': 'You can only review a rider after the order is delivered'}, status=400)
    if hasattr(delivery, 'review'):
        return JsonResponse({'error': 'You have already reviewed this rider'}, status=400)

    try:
        rating = int(request.POST.get('rating', 0))
    except (TypeError, ValueError):
        rating = 0
    if rating < 1 or rating > 5:
        return JsonResponse({'error': 'Please select a rating between 1 and 5 stars.'}, status=400)

    RiderReview.objects.create(
        delivery=delivery,
        rider=delivery.rider,
        user=request.user,
        rating=rating,
        comment=request.POST.get('comment', '').strip(),
    )
    delivery_services.notify_rider(
        delivery.rider,
        'New rider review ⭐',
        f'You received a {rating}-star rating from a customer for order #{order.order_id}.',
        kind='delivery',
        order=order,
        delivery=delivery,
        link='/riders/dashboard/',
    )
    return JsonResponse({'success': True})

@login_required(login_url='login')
def notifications_api(request):
    limit = _parse_int(request.GET.get('limit'), 20)
    query = db_models.Q(user=request.user)
    restaurant = Restaurant.objects.filter(owner=request.user).first()
    if restaurant:
        query |= db_models.Q(restaurant=restaurant)
    notifs = Notification.objects.filter(query)[:limit]
    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'link': n.link,
        'kind': n.kind,
        'is_read': n.is_read,
        'created_at': n.created_at.isoformat(),
    } for n in notifs]
    unread = Notification.objects.filter(query, is_read=False).count()
    return JsonResponse({'notifications': data, 'unread': unread})

@login_required(login_url='login')
def notifications_read_api(request):
    if request.method == 'POST':
        query = db_models.Q(user=request.user)
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if restaurant:
            query |= db_models.Q(restaurant=restaurant)
        Notification.objects.filter(query, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'POST required'}, status=405)

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

    restaurant = None
    restaurant_id = data.get('restaurant_id')
    if restaurant_id:
        try:
            restaurant = Restaurant.objects.get(pk=int(restaurant_id))
        except (TypeError, ValueError, Restaurant.DoesNotExist):
            restaurant = None
    if restaurant is None and restaurant_name:
        restaurant = Restaurant.objects.filter(name__iexact=restaurant_name).first()

    order = Order.objects.create(
        user=request.user,
        restaurant=restaurant,
        order_id=order_id,
        restaurant_name=restaurant.name if restaurant else restaurant_name,
        delivery_address=delivery_address,
        payment_method=payment_method,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount=discount,
        total=total,
        status='pending'
    )

    for item in items_data:
        OrderItem.objects.create(
            order=order,
            name=item.get('name', 'Item'),
            price=float(item.get('price', 0)),
            quantity=int(item.get('qty', 1)),
            image=item.get('image', '')
        )

    # Online payment methods (card / wallet) go through Paystack. The order
    # stays 'pending' until Paystack confirms the charge via webhook/callback.
    if payment_method in ('card', 'wallet'):
        channels = None
        if payment_method == 'wallet':
            channels = ['apple_pay', 'google_pay']
        try:
            payment = payment_services.initialize_payment(order, request, channels=channels)
        except PaystackError as exc:
            order.status = 'cancelled'
            order.save(update_fields=['status'])
            return JsonResponse({'error': str(exc)}, status=400)
        return JsonResponse({
            'success': True,
            'order_id': order_id,
            'total': total,
            'payment_url': payment['authorization_url'],
            'payment_reference': payment['reference'],
        })

    # Cash on delivery — confirm immediately.
    order.status = 'confirmed'
    order.is_accepted = True
    order.save(update_fields=['status', 'is_accepted'])

    send_order_confirmation_emails(order)

    return JsonResponse({
        'success': True,
        'order_id': order_id,
        'total': total
    })


@login_required(login_url='login')
@ensure_csrf_cookie
def dashboard_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    orders_data = []
    total_spent = 0
    for o in orders:
        items = [{'name': i.name, 'qty': i.quantity, 'price': float(i.price)} for i in o.items.all()]
        if o.status != 'cancelled':
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
    return render(request, 'dashboard.html', {
        'user_orders': orders_data,
        'stats': stats,
        'user_addresses': addresses_data,
        'user_avatar': profile_pics(request.user),
        'db_restaurants': build_restaurants_payload(),
    })

def profile_pics(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile.profile_picture.url if profile.profile_picture else ''

@login_required(login_url='login')
def profile_pics_api(request):
    if request.method == 'GET':
        return JsonResponse({'avatar': profile_pics(request.user)})
    if request.method == 'POST':
        if 'avatar_file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file selected'}, status=400)
        f = request.FILES['avatar_file']
        if not f.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'File must be an image'}, status=400)
        if f.size > 5 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'Image too large (max 5MB)'}, status=400)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if profile.profile_picture:
            profile.profile_picture.delete(save=False)
        profile.profile_picture = f
        profile.save()
        return JsonResponse({'success': True, 'avatar': profile.profile_picture.url})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required(login_url='login')
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


PANEL_SECTIONS = ['overview', 'orders', 'menu', 'categories', 'customers', 'reviews', 'inventory', 'coupons', 'payments', 'settings']

@login_required(login_url='login')
def restaurant_dashboard_view(request, section='overview'):
    if section not in PANEL_SECTIONS:
        section = 'overview'
    try:
        restaurant = Restaurant.objects.get(owner=request.user)
    except Restaurant.DoesNotExist:
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return render(request, 'restaurant_dashboard.html', {
                'no_restaurant': True,
                'active_section': 'overview',
                'hide_navbar': True,
            })

    today = timezone.now().date()
    orders_today = Order.objects.filter(restaurant=restaurant, created_at__date=today)
    all_orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')
    customers = User.objects.filter(orders__restaurant=restaurant).distinct()

    stats = {
        'today_revenue': sum(o.total for o in orders_today if o.status == 'delivered'),
        'total_orders': all_orders.count(),
        'pending_orders': all_orders.filter(status='pending').count(),
        'completed_orders': all_orders.filter(status='delivered').count(),
        'menu_items': MenuItem.objects.filter(restaurant=restaurant).count(),
        'customers': customers.count(),
        'orders_today': orders_today.count(),
    }

    low_stock = InventoryItem.objects.filter(restaurant=restaurant, stock__lte=db_models.F('low_stock_threshold'))
    recent_reviews = Review.objects.filter(restaurant=restaurant, is_hidden=False).order_by('-created_at')[:5]

    # Paginate orders
    page_number = request.GET.get('page', 1)
    paginator = Paginator(all_orders, 15)
    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)

    context = {
        'restaurant': restaurant,
        'stats': stats,
        'orders': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'orders_json': json.dumps([{
            'id': o.id, 'order_id': o.order_id, 'customer': safe_user_name(o),
            'items': [{'name': i.name, 'qty': i.quantity, 'price': float(i.price)} for i in o.items.all()],
            'total': float(o.total), 'status': o.status, 'payment': o.payment_method,
            'address': o.delivery_address, 'created_at': o.created_at.isoformat(),
            'is_accepted': o.is_accepted,
            'delivery': delivery_payload(getattr(o, 'delivery', None), include_otp=False),
        } for o in page_obj.object_list]),
        'orders_deliveries_json': json.dumps({
            o.id: delivery_payload(getattr(o, 'delivery', None), include_otp=False)
            for o in page_obj.object_list
        }),
        'menu_items': MenuItem.objects.filter(restaurant=restaurant).order_by('-created_at'),
        'menu_items_json': json.dumps([{
            'id': item.id,
            'name': item.name,
            'price': float(item.price),
            'discounted_price': float(item.discounted_price) if item.discounted_price else None,
            'category_id': item.category_id,
            'description': item.description,
            'image': item.image.url if item.image else '',
            'prep_time': item.prep_time,
            'calories': item.calories,
            'is_veg': item.is_veg,
            'is_featured': item.is_featured,
            'is_available': item.is_available,
        } for item in MenuItem.objects.filter(restaurant=restaurant)]),
        'categories': Category.objects.filter(restaurant=restaurant).order_by('name'),
        'inventory': InventoryItem.objects.filter(restaurant=restaurant).order_by('name'),
        'low_stock': low_stock,
        'coupons': Coupon.objects.filter(restaurant=restaurant).order_by('-created_at'),
        'reviews': recent_reviews,
        'customers_list': customers[:20],
        'order_statuses': [s[0] for s in Order.STATUS_CHOICES],
        'active_section': section,
        'hide_navbar': True,
    }


    return render(request, 'restaurant_dashboard.html', context)
@login_required
def restaurant_api_view(request):
    try:
        restaurant = Restaurant.objects.get(owner=request.user)
    except Restaurant.DoesNotExist:
        return JsonResponse({'error': 'No restaurant found'}, status=404)

    action = request.GET.get('action') or request.POST.get('action')

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                action = data.get('action', action)
            except json.JSONDecodeError:
                data = request.POST
        else:
            data = request.POST

    # === ORDER ACTIONS ===
    if action == 'update_order_status':
        order_id = data.get('order_id')
        new_status = data.get('status')
        try:
            order = Order.objects.get(id=order_id, restaurant=restaurant)
            if new_status == 'ready':
                delivery_services.create_delivery_for_order(order)
                order.status = 'ready'
                order.is_accepted = True
                order.save()
                delivery_services.notify_user(
                    order.user, 'Order ready for pickup 📦',
                    f'Your order #{order.order_id} from {restaurant.name} is ready. We are finding a rider for you.',
                    kind='order', order=order,
                    link='/tracking/',
                )
            elif new_status == 'delivered':
                if hasattr(order, 'delivery'):
                    delivery_services.force_complete_delivery(order.delivery)
                else:
                    order.status = 'delivered'
                    order.save()
            elif new_status == 'cancelled':
                if hasattr(order, 'delivery'):
                    delivery_services.cancel_delivery(order.delivery, 'Cancelled by the restaurant')
                else:
                    order.status = 'cancelled'
                    order.save()
                    delivery_services.notify_user(
                        order.user, 'Order cancelled',
                        f'Your order #{order.order_id} was cancelled by the restaurant.',
                        kind='order', order=order,
                        link='/tracking/',
                    )
            else:
                order.status = new_status
                if new_status in ('confirmed', 'preparing'):
                    order.is_accepted = True
                order.save()
                if new_status == 'confirmed':
                    delivery_services.notify_user(
                        order.user, 'Order confirmed ✅',
                        f'{restaurant.name} accepted your order #{order.order_id}.',
                        kind='order', order=order,
                        link='/tracking/',
                    )
                elif new_status == 'preparing':
                    delivery_services.notify_user(
                        order.user, 'Order is being prepared 👨‍🍳',
                        f'{restaurant.name} is preparing your order #{order.order_id}.',
                        kind='order', order=order,
                        link='/tracking/',
                    )
            return JsonResponse({'success': True, 'status': order.status})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

    elif action == 'accept_order':
        order_id = data.get('order_id')
        try:
            order = Order.objects.get(id=order_id, restaurant=restaurant)
            if order.status in ('pending',):
                order.status = 'confirmed'
                order.is_accepted = True
                order.save()
                delivery_services.notify_user(
                    order.user, 'Order confirmed ✅',
                    f'{restaurant.name} accepted your order #{order.order_id}.',
                    kind='order', order=order,
                    link='/tracking/',
                )
            return JsonResponse({'success': True, 'status': order.status})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

    elif action == 'reject_order':
        order_id = data.get('order_id')
        try:
            order = Order.objects.get(id=order_id, restaurant=restaurant)
            order.status = 'cancelled'
            order.is_accepted = False
            order.save()
            delivery_services.notify_user(
                order.user, 'Order rejected',
                f'{restaurant.name} could not accept your order #{order.order_id}.',
                kind='order', order=order,
                link='/tracking/',
            )
            return JsonResponse({'success': True, 'status': order.status})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

    elif action == 'get_order_delivery':
        order_id = data.get('order_id')
        try:
            order = Order.objects.get(id=order_id, restaurant=restaurant)
            delivery = getattr(order, 'delivery', None)
            return JsonResponse({'success': True, 'delivery': delivery_payload(delivery, include_otp=False)})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

    elif action == 'cancel_order':
        order_id = data.get('order_id')
        try:
            order = Order.objects.get(id=order_id, restaurant=restaurant)
            order.status = 'cancelled'
            order.save()
            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

    # === MENU ACTIONS ===
    elif action == 'get_menu_items':
        items = [{
            'id': it.id, 'name': it.name, 'price': float(it.price),
            'discounted_price': float(it.discounted_price) if it.discounted_price else None,
            'category_id': it.category_id, 'description': it.description,
            'image': it.image.url if it.image else '', 'prep_time': it.prep_time, 'calories': it.calories,
            'is_veg': it.is_veg, 'is_featured': it.is_featured, 'is_available': it.is_available,
        } for it in MenuItem.objects.filter(restaurant=restaurant).order_by('-created_at')]
        return JsonResponse({'success': True, 'items': items})

    elif action == 'create_menu_item':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = request.POST
        else:
            data = request.POST
        image = ''
        if request.FILES.get('image_file'):
            img_file = request.FILES['image_file']
            fs = FileSystemStorage()
            filename = fs.save(f'menu_items/{img_file.name}', img_file)
            image = filename
        price = _parse_decimal(data.get('price'))
        if price is None:
            return JsonResponse({'error': 'Invalid price'}, status=400)
        item = MenuItem.objects.create(
            restaurant=restaurant, name=data.get('name'),
            description=data.get('description', ''),
            price=price, discounted_price=_parse_decimal(data.get('discounted_price')),
            category_id=data.get('category_id') or None,
            image=image, prep_time=_parse_int(data.get('prep_time'), 10),
            is_available=data.get('is_available', True),
            is_featured=data.get('is_featured', False),
            is_veg=data.get('is_veg', False), calories=_parse_int(data.get('calories'), 0),
        )
        return JsonResponse({'success': True, 'id': item.id, 'image': item.image.url if item.image else ''})

    elif action == 'update_menu_item':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = request.POST
        else:
            data = request.POST
        try:
            item = MenuItem.objects.get(id=data.get('id'), restaurant=restaurant)
            for field in ['name', 'description', 'image']:
                if field in data: setattr(item, field, data[field])
            for bool_field in ['is_available', 'is_featured', 'is_veg', 'is_popular']:
                if bool_field in data: setattr(item, bool_field, data[bool_field])
            if 'price' in data:
                price = _parse_decimal(data['price'])
                if price is None:
                    return JsonResponse({'error': 'Invalid price'}, status=400)
                item.price = price
            if 'discounted_price' in data:
                item.discounted_price = _parse_decimal(data['discounted_price'])
            if 'prep_time' in data:
                item.prep_time = _parse_int(data['prep_time'], item.prep_time)
            if 'calories' in data:
                item.calories = _parse_int(data['calories'], item.calories)
            if 'category_id' in data:
                item.category_id = data['category_id'] or None
            if request.FILES.get('image_file'):
                img_file = request.FILES['image_file']
                fs = FileSystemStorage()
                filename = fs.save(f'menu_items/{img_file.name}', img_file)
                item.image = filename
            elif 'image' in data and not data.get('image'):
                item.image = ''
            item.save()
            return JsonResponse({'success': True, 'image': item.image.url if item.image else ''})
        except MenuItem.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)

    elif action == 'delete_menu_item':
        try:
            MenuItem.objects.get(id=data.get('id'), restaurant=restaurant).delete()
            return JsonResponse({'success': True})
        except MenuItem.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)

    # === CATEGORY ACTIONS ===
    elif action == 'create_category':
        cat = Category.objects.create(restaurant=restaurant, name=data.get('name'), emoji=data.get('emoji', ''))
        return JsonResponse({'success': True, 'id': cat.id, 'name': cat.name})

    elif action == 'update_category':
        try:
            cat = Category.objects.get(id=data.get('id'), restaurant=restaurant)
            cat.name = data.get('name', cat.name)
            cat.emoji = data.get('emoji', cat.emoji)
            if 'is_available' in data: cat.is_available = data['is_available']
            cat.save()
            return JsonResponse({'success': True})
        except Category.DoesNotExist:
            return JsonResponse({'error': 'Category not found'}, status=404)

    elif action == 'delete_category':
        try:
            Category.objects.get(id=data.get('id'), restaurant=restaurant).delete()
            return JsonResponse({'success': True})
        except Category.DoesNotExist:
            return JsonResponse({'error': 'Category not found'}, status=404)

    # === INVENTORY ACTIONS ===
    elif action == 'update_inventory':
        try:
            inv = InventoryItem.objects.get(id=data.get('id'), restaurant=restaurant)
            inv.stock = data.get('stock', inv.stock)
            inv.save()
            return JsonResponse({'success': True, 'stock': float(inv.stock)})
        except InventoryItem.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)

    # === SETTINGS ===
    elif action == 'update_settings':
        for field in ['name', 'description', 'cuisine', 'address', 'phone', 'email', 'logo', 'cover_image',
                       'delivery_fee', 'delivery_radius', 'tax_rate', 'min_order', 'is_open']:
            if field in data: setattr(restaurant, field, data[field])
        if data.get('opening_time'): restaurant.opening_time = data['opening_time']
        if data.get('closing_time'): restaurant.closing_time = data['closing_time']
        if request.FILES.get('logo_file'):
            logo_file = request.FILES['logo_file']
            fs = FileSystemStorage()
            filename = fs.save(f'restaurant_logos/{logo_file.name}', logo_file)
            restaurant.logo = fs.url(filename)
        if request.FILES.get('cover_file'):
            cover_file = request.FILES['cover_file']
            fs = FileSystemStorage()
            filename = fs.save(f'restaurant_covers/{cover_file.name}', cover_file)
            restaurant.cover_image = fs.url(filename)
        restaurant.save()
        return JsonResponse({'success': True, 'logo': restaurant.logo, 'cover_image': restaurant.cover_image})

    # === REVIEW ACTIONS ===
    elif action == 'reply_review':
        try:
            rev = Review.objects.get(id=data.get('id'), restaurant=restaurant)
            rev.reply = data.get('reply', '')
            rev.save()
            return JsonResponse({'success': True})
        except Review.DoesNotExist:
            return JsonResponse({'error': 'Review not found'}, status=404)

    elif action == 'hide_review':
        try:
            rev = Review.objects.get(id=data.get('id'), restaurant=restaurant)
            rev.is_hidden = True
            rev.save()
            return JsonResponse({'success': True})
        except Review.DoesNotExist:
            return JsonResponse({'error': 'Review not found'}, status=404)

    # === COUPON ACTIONS ===
    elif action == 'create_coupon':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = request.POST
        else:
            data = request.POST
        Coupon.objects.create(
            restaurant=restaurant, code=data.get('code', '').upper(),
            discount_type=data.get('discount_type', 'percent'),
            discount_value=data.get('discount_value', 0),
            min_order=data.get('min_order', 0),
            max_uses=data.get('max_uses', 0),
            expires_at=data.get('expires_at') or None,
        )
        return JsonResponse({'success': True})

    elif action == 'delete_coupon':
        try:
            Coupon.objects.get(id=data.get('id'), restaurant=restaurant).delete()
            return JsonResponse({'success': True})
        except Coupon.DoesNotExist:
            return JsonResponse({'error': 'Coupon not found'}, status=404)

    elif action == 'customer_action':
        try:
            user = User.objects.get(id=data.get('user_id'))
            if data.get('block') == 'true':
                user.is_active = False
            else:
                user.is_active = True
            user.save()
            return JsonResponse({'success': True, 'is_active': user.is_active})
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)

    return JsonResponse({'error': 'Invalid action'}, status=400)



@ensure_csrf_cookie
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
    coupons = [{
        'code': c.code,
        'type': c.discount_type,
        'value': float(c.discount_value),
        'minOrder': float(c.min_order),
        'maxUses': c.max_uses,
        'timesUsed': c.times_used,
        'label': f"{float(c.discount_value):g}% off your order" if c.discount_type == 'percent' else f"₦{float(c.discount_value):g} off your order",
        'expiresAt': c.expires_at.isoformat() if c.expires_at else None,
    } for c in Coupon.objects.filter(is_active=True)]
    return render(request, 'cart.html', {
        'user_addresses_json': addresses,
        'coupons_json': coupons,
    })
