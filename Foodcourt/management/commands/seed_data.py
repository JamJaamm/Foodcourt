from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Foodcourt.models import Restaurant, Category, MenuItem, InventoryItem, Coupon, Review, Order, OrderItem, Address
from datetime import datetime, timedelta
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Seed the database with sample restaurant, menu, and order data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding data...')

        # Create superuser
        admin, _ = User.objects.get_or_create(username='admin', defaults={
            'email': 'admin@foodcourt.com', 'is_staff': True, 'is_superuser': True, 'is_active': True,
        })
        if _:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created superuser: admin / admin123'))

        # Create test user
        test_user, _ = User.objects.get_or_create(username='test@foodcourt.com', defaults={
            'email': 'test@foodcourt.com', 'first_name': 'Test', 'last_name': 'User', 'is_active': True,
        })
        if _:
            test_user.set_password('test123')
            test_user.save()
            self.stdout.write(self.style.SUCCESS('Created test user: test@foodcourt.com / test123'))

        # Create restaurant owned by admin
        restaurant, created = Restaurant.objects.get_or_create(
            owner=admin,
            defaults={
                'name': 'Bella Napoli Pizzeria',
                'description': 'Authentic Italian wood-fired pizzas made with fresh ingredients imported directly from Italy. Our dough is fermented for 48 hours for the perfect crust.',
                'cuisine': 'Italian, Pizza',
                'address': '42 Park Street, New Delhi, 110001',
                'phone': '+91 98765 43210',
                'email': 'hello@bellanapoli.foodcourt.com',
                'logo': 'https://img.freepik.com/free-vector/flat-design-italian-restaurant-logo_23-2149195116.jpg',
                'cover_image': 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1200&q=80',
                'delivery_fee': 2.99,
                'rating': 4.7,
                'is_open': True,
                'opening_time': datetime.strptime('09:00', '%H:%M').time(),
                'closing_time': datetime.strptime('23:00', '%H:%M').time(),
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created restaurant: {restaurant.name}'))
        else:
            self.stdout.write(f'Restaurant already exists: {restaurant.name}')

        # Categories
        categories_data = [
            ('', 'Pizzas', True),
            ('', 'Starters & Salads', True),
            ('', 'Pasta', True),
            ('', 'Beverages', True),
            ('', 'Desserts', True),
        ]
        cat_map = {}
        for emoji, name, avail in categories_data:
            cat, created = Category.objects.get_or_create(
                restaurant=restaurant, name=name,
                defaults={'emoji': emoji, 'is_available': avail}
            )
            cat_map[name] = cat
            if created:
                self.stdout.write(f'  Created category: {name}')

        # Menu items
        menu_data = [
            ('Margherita Pizza', 'Classic tomato sauce, fresh mozzarella, basil', 12.99, None, True, False, True, 'Pizzas', 249, 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400&q=80'),
            ('Pepperoni Pizza', 'Double pepperoni, mozzarella, house tomato sauce', 14.99, 12.99, True, True, False, 'Pizzas', 289, 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=400&q=80'),
            ('Quattro Formaggi', 'Four cheese blend: mozzarella, gorgonzola, parmesan, ricotta', 16.99, None, True, False, True, 'Pizzas', 299, 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&q=80'),
            ('Bruschetta', 'Toasted bread with tomato, basil, garlic, olive oil', 8.99, None, True, False, True, 'Starters & Salads', 189, 'https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=400&q=80'),
            ('Caesar Salad', 'Romaine, parmesan, croutons, house Caesar dressing', 9.99, None, True, False, False, 'Starters & Salads', 199, 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400&q=80'),
            ('Caprese Salad', 'Fresh mozzarella, tomatoes, basil, balsamic glaze', 10.99, None, True, False, False, 'Starters & Salads', 179, 'https://images.unsplash.com/photo-1608897013039-887f21d8c804?w=400&q=80'),
            ('Spaghetti Carbonara', 'Egg, parmesan, pancetta, black pepper', 13.99, None, True, False, True, 'Pasta', 299, 'https://images.unsplash.com/photo-1612874742237-6526221588e3?w=400&q=80'),
            ('Penne Arrabbiata', 'Spicy tomato sauce, garlic, chilli, fresh parsley', 11.99, None, True, False, False, 'Pasta', 249, 'https://images.unsplash.com/photo-1608219992759-8d74ed8d76eb?w=400&q=80'),
            ('Fettuccine Alfredo', 'Creamy parmesan sauce, garlic, fresh herbs', 13.99, None, True, False, False, 'Pasta', 299, 'https://images.unsplash.com/photo-1645112411341-6c4fd023714a?w=400&q=80'),
            ('Tiramisu', 'Coffee-soaked ladyfingers, mascarpone, cocoa', 7.99, None, True, False, True, 'Desserts', 149, 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400&q=80'),
            ('Panna Cotta', 'Vanilla cream with berry compote', 6.99, None, True, False, False, 'Desserts', 129, 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400&q=80'),
        ]

        for name, desc, price, disc_price, avail, popular, featured, cat_name, cal, img in menu_data:
            _, created = MenuItem.objects.get_or_create(
                restaurant=restaurant, name=name,
                defaults={
                    'category': cat_map[cat_name], 'description': desc,
                    'price': price, 'discounted_price': disc_price,
                    'is_available': avail, 'is_popular': popular, 'is_featured': featured,
                    'calories': cal, 'image': img, 'prep_time': random.choice([12, 15, 18, 20, 25]),
                }
            )
            if created:
                self.stdout.write(f'  Created menu item: {name}')

        # Inventory items
        inventory_data = [
            ('Pizza Dough (kg)', 25, 10, 'kg'),
            ('Mozzarella (kg)', 15, 5, 'kg'),
            ('Tomato Sauce (L)', 20, 5, 'L'),
            ('Pasta (kg)', 30, 10, 'kg'),
            ('Olive Oil (L)', 12, 3, 'L'),
            ('Basil (bunch)', 8, 5, 'units'),
            ('Coffee Beans (kg)', 5, 2, 'kg'),
            ('Napkins (pack)', 45, 20, 'units'),
        ]
        for name, stock, threshold, unit in inventory_data:
            _, created = InventoryItem.objects.get_or_create(
                restaurant=restaurant, name=name,
                defaults={'stock': stock, 'unit': unit, 'low_stock_threshold': threshold}
            )
            if created:
                self.stdout.write(f'  Created inventory: {name}')

        # Coupons
        coupon_data = [
            ('WELCOME10', 'percent', 10, 20, 100),
            ('FREEDEL', 'fixed', 2.99, 15, 50),
            ('PIZZA20', 'percent', 20, 25, 50),
        ]
        for code, dtype, dval, min_ord, max_use in coupon_data:
            _, created = Coupon.objects.get_or_create(
                restaurant=restaurant, code=code,
                defaults={
                    'discount_type': dtype, 'discount_value': dval,
                    'min_order': min_ord, 'max_uses': max_use,
                    'expires_at': timezone.now() + timedelta(days=90),
                }
            )
            if created:
                self.stdout.write(f'  Created coupon: {code}')

        # Seed orders for the restaurant
        menu_items = MenuItem.objects.filter(restaurant=restaurant)
        if menu_items.exists():
            existing = Order.objects.filter(restaurant=restaurant).count()
            if existing < 30:
                statuses = ['pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery', 'delivered']
                needed = 30 - existing
                for i in range(needed):
                    days_ago = random.randint(0, 30)
                    order_time = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 12))
                    user = test_user if i % 2 == 0 else admin
                    num_items = random.randint(1, 4)
                    selected = random.sample(list(menu_items), min(num_items, len(menu_items)))
                    subtotal = sum(float(m.price) for m in selected)
                    delivery_fee = float(restaurant.delivery_fee)
                    discount = round(random.uniform(0, 3), 2) if i % 3 == 0 else 0
                    total = round(subtotal + delivery_fee - discount, 2)
                    status = random.choice(statuses)
                    order_id = f'FC-{order_time.year}-{random.randint(1000, 9999)}'
                    order = Order.objects.create(
                        user=user, restaurant=restaurant, order_id=order_id,
                        restaurant_name=restaurant.name,
                        delivery_address=f'Sample Address #{existing + i + 1}',
                        payment_method=random.choice(['cash', 'card', 'online']),
                        subtotal=subtotal, delivery_fee=delivery_fee,
                        discount=discount, total=total, status=status,
                        is_accepted=status not in ('pending',),
                        created_at=order_time,
                    )
                    for m in selected:
                        OrderItem.objects.create(order=order, name=m.name, price=float(m.price), quantity=random.randint(1, 3), image=m.image)
                    self.stdout.write(f'  Created order {order_id} [{status}] ({user.email})')
            else:
                self.stdout.write(f'  {existing} orders already exist, skipping')

        # Seed an address for test user
        Address.objects.get_or_create(
            user=test_user, label='Home',
            defaults={
                'street': '42 Park Street', 'landmark': 'Near Central Park',
                'city': 'New Delhi', 'state': 'Delhi', 'country': 'India',
                'phone': '+91 98765 43210', 'is_default': True,
            }
        )

        self.stdout.write(self.style.SUCCESS('\nSeed complete!'))
        self.stdout.write('  Admin login:  admin / admin123')
        self.stdout.write('  Test user:    test@foodcourt.com / test123')
        self.stdout.write(f'  Restaurant:   {restaurant.name}')
