from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django_resized import ResizedImageField 

class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='verification_codes')
    rider = models.ForeignKey('Riders', on_delete=models.CASCADE, null=True, blank=True, related_name='verification_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > 600

    def __str__(self):
        return f"{self.user.email} - {self.code}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile({self.user.email})"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'), ('ready', 'Ready'),
        ('out_for_delivery', 'Out for Delivery'), ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    restaurant = models.ForeignKey('Restaurant', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_id = models.CharField(max_length=20, unique=True)
    restaurant_name = models.CharField(max_length=200, default='')
    delivery_address = models.TextField()
    payment_method = models.CharField(max_length=20)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_accepted = models.BooleanField(default=False)
    rider = models.ForeignKey('Riders', on_delete=models.SET_NULL, null=True, blank=True, related_name='delivery_orders')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def payment_status(self):
        payment = getattr(self, 'payment', None)
        return payment.status if payment else None

    @property
    def is_paid(self):
        return self.payment_status == 'successful'

    def __str__(self):
        return f"{self.order_id} - {self.user.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    image = models.URLField(blank=True, default='')

    def __str__(self):
        return f"{self.name} x{self.quantity}"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=100)
    street = models.CharField(max_length=255, default='')
    landmark = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=100, default='')
    state = models.CharField(max_length=100, default='')
    country = models.CharField(max_length=100, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_address(self):
        parts = [self.street]
        if self.landmark:
            parts.append(f"Near {self.landmark}")
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country:
            parts.append(self.country)
        return ', '.join(parts)

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    def __str__(self):
        return f"{self.label}: {self.full_address[:50]}"


class Restaurant(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurants')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    cuisine = models.CharField(max_length=100, blank=True, default='')
    address = models.TextField(blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    logo = models.URLField(blank=True, default='')
    cover_image = models.URLField(blank=True, default='')
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    is_open = models.BooleanField(default=True)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=2.99)
    delivery_radius = models.DecimalField(max_digits=6, decimal_places=1, default=10.0)
    tax_rate = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    min_order = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    opening_time = models.TimeField(default='08:00')
    closing_time = models.TimeField(default='23:00')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    def __str__(self):
        return self.name


class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    emoji = models.CharField(max_length=10, blank=True, default='')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='menu_items/', blank=True, default='')
    prep_time = models.IntegerField(default=10)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_veg = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    calories = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def effective_price(self):
        return self.discounted_price if self.discounted_price else self.price


class InventoryItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='inventory')
    name = models.CharField(max_length=200)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default='units')
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.stock} {self.unit})"


class Coupon(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='coupons')
    code = models.CharField(max_length=50)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('fixed', 'Fixed Amount')])
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    min_order = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_uses = models.IntegerField(default=0)
    times_used = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class Review(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    rating = models.IntegerField()
    comment = models.TextField(blank=True, default='')
    is_hidden = models.BooleanField(default=False)
    is_reported = models.BooleanField(default=False)
    reply = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.rating}*"


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    PREPARING = "PREPARING", "Preparing"
    READY = "READY", "Ready for Pickup"
    RIDER_ASSIGNED = "RIDER_ASSIGNED", "Rider Assigned"
    ON_THE_WAY = "ON_THE_WAY", "On The Way"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


#  RIDERS MODELS


class Riders(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=200, default='')
    last_name = models.CharField(max_length=200, default='')
    phone = models.CharField(max_length=30, default='')
    gender = models.CharField(max_length=20, blank=True, default='')
    dob = models.DateField(null=True, blank=True)
    avatar = models.CharField(max_length=500, blank=True, default='')
    avatar_image = models.ImageField(upload_to='rider_pics', blank=True, null=True)
    address = models.TextField(default='')
    city = models.CharField(max_length=200, default='')
    state = models.CharField(max_length=200, default='')
    country = models.CharField(max_length=200, default='')
    postal_code = models.CharField(max_length=50, blank=True, default='')
    vehicle_type = models.CharField(max_length=100, default='')
    vehicle_brand = models.CharField(max_length=200, default='')
    vehicle_model = models.CharField(max_length=200, default='')
    vehicle_color = models.CharField(max_length=100, default='')
    vehicle_plate = models.CharField(max_length=100, default='')
    bank_name = models.CharField(max_length=200, default='')
    account_name = models.CharField(max_length=200, default='')
    account_number = models.CharField(max_length=30, default='')
    documents = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    location = models.CharField(max_length=500, blank=True, default='')
    payments = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Riders'
        managed = True
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


#  DELIVERY MODELS


class Delivery(models.Model):
    STATUS_CHOICES = [
        ('searching', 'Searching for Rider'),
        ('assigned', 'Rider Assigned'),
        ('arrived_at_restaurant', 'Arrived at Restaurant'),
        ('picked_up', 'Picked Up'),
        ('on_the_way', 'On The Way'),
        ('arrived', 'Arrived'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery')
    rider = models.ForeignKey('Riders', on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='searching')
    otp = models.CharField(max_length=6, blank=True, default='')
    otp_attempts = models.IntegerField(default=0)
    payout = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    declined_by = models.ManyToManyField('Riders', blank=True, related_name='declined_deliveries')
    notified_riders = models.ManyToManyField('Riders', blank=True, related_name='notified_deliveries')
    accepted_at = models.DateTimeField(null=True, blank=True)
    arrived_at_restaurant_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    on_the_way_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ACTIVE_STATUSES = ['assigned', 'arrived_at_restaurant', 'picked_up', 'on_the_way', 'arrived']

    def __str__(self):
        return f"Delivery {self.pk} - {self.order.order_id} ({self.status})"

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class DeliveryStatusLog(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(max_length=30)
    label = models.CharField(max_length=100, default='')
    note = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.delivery_id} - {self.label}"


class Notification(models.Model):
    KIND_CHOICES = [
        ('info', 'Info'),
        ('order', 'Order'),
        ('delivery', 'Delivery'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    rider = models.ForeignKey('Riders', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, default='')
    link = models.CharField(max_length=300, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class RiderReview(models.Model):
    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE, related_name='review')
    rider = models.ForeignKey('Riders', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rider_reviews')
    rating = models.IntegerField()
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} -> {self.rider.email} ({self.rating}*)"


class AdminAction(models.Model):
    ACTION_CHOICES = [
        ('block_user', 'Blocked user'),
        ('unblock_user', 'Unblocked user'),
        ('resend_verification', 'Resent verification email'),
        ('delete_user', 'Deleted user'),
        ('bulk_block', 'Bulk blocked users'),
        ('bulk_unblock', 'Bulk unblocked users'),
        ('export_users', 'Exported users'),
    ]
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='admin_actions')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_actions_received')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    details = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.admin} -> {self.get_action_display()} -> {self.target_user}"


class DeliverySettings(models.Model):
    tier_0_2 = models.DecimalField(max_digits=8, decimal_places=2, default=700, verbose_name='0–2 km fee')
    tier_2_5 = models.DecimalField(max_digits=8, decimal_places=2, default=1200, verbose_name='2–5 km fee')
    tier_5_8 = models.DecimalField(max_digits=8, decimal_places=2, default=1700, verbose_name='5–8 km fee')
    tier_8_12 = models.DecimalField(max_digits=8, decimal_places=2, default=2300, verbose_name='8–12 km fee')
    tier_12_15 = models.DecimalField(max_digits=8, decimal_places=2, default=3000, verbose_name='12–15 km fee')
    max_distance_km = models.DecimalField(max_digits=6, decimal_places=1, default=15.0, verbose_name='Maximum delivery distance (km)')
    surge_enabled = models.BooleanField(default=False, verbose_name='Surge pricing enabled')
    surge_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.00, verbose_name='Surge multiplier')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Delivery Settings'
        verbose_name_plural = 'Delivery Settings'

    def __str__(self):
        return f"Delivery Settings (max {self.max_distance_km} km)"

    @classmethod
    def get_active(cls):
        settings_obj, _ = cls.objects.get_or_create(pk=1)
        return settings_obj


