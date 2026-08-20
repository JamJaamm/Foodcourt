# FoodCourt

A full-stack food delivery platform built with Django. Customers browse restaurants, place orders, and track deliveries in real time. Restaurant owners manage menus and orders. Riders handle pickups and drop-offs with OTP-verified delivery. A general admin dashboard provides platform-wide oversight.

Live deployment target: [Render](https://render.com)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Models](#models)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [User Roles](#user-roles)
- [API Endpoints](#api-endpoints)
- [Payment Integration](#payment-integration)
- [Email System](#email-system)
- [Map & Location System](#map--location-system)
- [Delivery Fee Calculation](#delivery-fee-calculation)
- [Default Admin](#default-admin)
- [License](#license)

---

## Features

### Customer
- Browse restaurants by cuisine, rating, and availability
- View restaurant menus with categories, prices, prep time, and dietary flags (veg, featured, popular)
- Add items to cart with quantity controls (localStorage-based cart)
- Save multiple delivery addresses (Home, Work, Other) with map-based or current-location pinning
- Pay via Paystack (card, bank transfer, USSD) or Cash on Delivery
- Live order tracking with status updates
- Rate restaurants and riders after delivery
- Email notifications for order confirmations and status changes

### Restaurant Owner
- Partner registration with structured address (Country, State, LGA, Area, Street, Landmark)
- Interactive dashboard: orders, menu, categories, customers, reviews, inventory, coupons, payments, settings
- Real-time order management (accept, reject, update status)
- Menu CRUD with image uploads, pricing, prep time, and availability toggles
- Category management with emoji icons
- Inventory tracking with low-stock alerts
- Coupon creation (percent/fixed discount, min order, usage limits, expiry)
- Map-based or current-location pinning for restaurant location

### Rider
- Separate registration and login flow
- Profile with personal info, vehicle details, bank details, and document uploads
- Admin approval workflow (pending → verified → approved/rejected)
- Online/offline toggle
- Accept or decline delivery assignments
- Update delivery status (picked up → on the way → delivered)
- OTP-based delivery confirmation
- Earnings tracking and rider reviews

### Admin
- Full platform dashboard with stats (users, orders, restaurants, riders)
- Restaurant management with location status display
- User management (block/unblock, resend verification, delete)
- Rider approval workflow (approve/reject with email notification)
- Delivery fee tier configuration with surge pricing
- Audit log of all admin actions
- User export

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 4.2, Django REST Framework 3.16, Django Channels |
| **Database** | MySQL (local), PostgreSQL (Render) |
| **Frontend** | Vanilla HTML/CSS/JS, Bootstrap 5.3, Font Awesome 6.5, Leaflet 1.9.4 |
| **Email** | Resend API |
| **Payments** | Paystack (NGN) |
| **Static Files** | WhiteNoise |
| **Maps** | Leaflet.js + OpenStreetMap tiles |
| **Geocoding** | Nominatim (fallback), browser Geolocation API + Leaflet map picker (primary) |
| **Production Server** | Gunicorn |
| **Deployment** | Render |
| **Python** | 3.12+ |

---

## Project Structure

```
Foodcourt/
├── Foodcourt/                  # Main Django project package
│   ├── settings.py
│   ├── urls.py
│   ├── views.py                # All view logic (~2800 lines)
│   ├── models.py               # 19 models
│   ├── geocoding.py            # Nominatim geocoding service
│   ├── delivery_service.py     # Distance calculation (OSRM + Haversine) and fee tiers
│   ├── notifications.py        # Resend-backed email sending
│   ├── patches.py              # Python 3.14 / Django 4.2 compatibility fix
│   ├── admin.py
│   ├── management/
│   │   └── commands/
│   │       ├── create_admin.py # Creates default admin superuser
│   │       └── seed_data.py    # Seed sample data
│   └── migrations/
├── payments/                   # Payments Django app
│   ├── models.py               # Payment model
│   ├── urls.py
│   └── views.py                # Paystack integration
├── static/
│   ├── css/
│   │   ├── variables.css       # Design tokens (colors, typography, spacing)
│   │   ├── base.css            # Global reset and typography
│   │   ├── components.css      # Navbar, buttons, cards, badges, forms, etc.
│   │   ├── animations.css      # Keyframes and animation utilities
│   │   ├── foodcourt-loader.css # Full-screen loading animation
│   │   └── pages/              # Page-specific styles
│   │       ├── auth.css
│   │       ├── cart.css
│   │       ├── dashboard.css
│   │       ├── index.css
│   │       ├── restaurant_detail.css
│   │       ├── restaurants.css
│   │       ├── rider.css
│   │       └── tracking.css
│   ├── js/
│   │   ├── app.js              # Global app logic
│   │   ├── cart.js             # Cart and checkout
│   │   ├── dashboard.js        # Customer dashboard
│   │   ├── data.js             # Static data
│   │   ├── foodcourt-loader.js # Loading animation controller
│   │   ├── index.js            # Homepage
│   │   ├── locations_data.js   # Country/State/LGA cascading dropdowns
│   │   ├── map-picker.js       # Leaflet map + geolocation picker
│   │   ├── restaurants.js      # Restaurant listing
│   │   ├── restaurant_detail.js # Restaurant detail page
│   │   ├── rider.js            # Rider portal
│   │   └── tracking.js         # Order tracking
│   └── images/
├── templates/
│   ├── base.html               # Base layout (navbar, Leaflet, Bootstrap, Font Awesome)
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── verify.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   ├── reset_password_done.html
│   ├── dashboard.html          # Customer dashboard (orders, addresses, favorites)
│   ├── admin_dashboard.html    # General admin panel
│   ├── restaurant_register.html
│   ├── restaurant_dashboard.html # Restaurant owner dashboard
│   ├── restaurants.html
│   ├── restaurant_detail.html
│   ├── cart.html               # Cart and checkout
│   ├── order_tracking.html
│   ├── terms.html
│   ├── privacy.html
│   ├── emails/                 # Transactional email templates
│   │   ├── welcome_email.html
│   │   ├── verify_email.html
│   │   ├── password_reset_email.html
│   │   ├── order_confirmation.html
│   │   ├── order_restaurant_notification.html
│   │   ├── rider_welcome_email.html
│   │   ├── rider_verify_email.html
│   │   ├── rider_approved_email.html
│   │   └── rider_rejected_email.html
│   ├── Riders/
│   │   ├── rider.html
│   │   ├── rider_login.html
│   │   ├── rider_dashboard.html
│   │   ├── rider_verify.html
│   │   ├── rider_forgot_password.html
│   │   └── rider_reset_password.html
│   └── payments/
│       ├── result.html
│       └── receipt.html
├── media/                      # User-uploaded files
├── requirements.txt
├── manage.py
├── build.sh                    # Render build script
├── .env.example
├── .gitignore
└── README.md
```

---

## Models

### Core

| Model | Purpose |
|-------|---------|
| `Restaurant` | Restaurant profile with structured address, coordinates, cuisine, hours, delivery settings |
| `MenuItem` | Individual menu item with price, image, prep time, dietary flags |
| `Category` | Menu category with emoji icon and availability toggle |
| `InventoryItem` | Stock tracking per restaurant |
| `Coupon` | Discount codes (percent or fixed, min order, usage limits, expiry) |
| `Review` | Customer reviews with rating, comment, and owner reply |

### Orders & Delivery

| Model | Purpose |
|-------|---------|
| `Order` | Full order lifecycle: items, status, delivery address, payment, totals |
| `OrderItem` | Line item within an order |
| `Delivery` | Delivery tracking: rider assignment, OTP, payout, status timestamps |
| `DeliveryStatusLog` | Audit log for delivery status changes |
| `DeliverySettings` | Global singleton: fee tiers (0-2km through 12-15km), max distance, surge pricing |

### Users & Auth

| Model | Purpose |
|-------|---------|
| `Profile` | Extends Django User with profile picture and phone |
| `Address` | Saved delivery addresses with structured fields and coordinates |
| `VerificationCode` | 6-digit OTP for email/phone verification |
| `Riders` | Custom rider model with credentials, vehicle/bank details, status workflow |
| `Notification` | In-app notifications for users, riders, and restaurants |

### Payments & Admin

| Model | Purpose |
|-------|---------|
| `Payment` | Paystack payment attempts with status and gateway response |
| `AdminAction` | Audit log of admin actions (block, delete, export, etc.) |
| `RiderReview` | Customer ratings and reviews for riders |

---

## Setup & Installation

### Prerequisites

- Python 3.12+
- MySQL 8.0+ (local) or PostgreSQL (production)
- pip

### Local Development

```bash
# Clone the repository
git clone https://github.com/JamJaamm/Foodcourt.git
cd Foodcourt

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your actual API keys

# Create the MySQL database
mysql -u root -e "CREATE DATABASE foodcourt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run migrations
python manage.py migrate

# Create default admin superuser
python manage.py create_admin

# Collect static files
python manage.py collectstatic --no-input

# Start development server
python manage.py runserver
```

The app runs at `http://127.0.0.1:8000`

### Default Admin Credentials

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
# Paystack (https://dashboard.paystack.com/#/settings/developers)
PAYSTACK_PUBLIC_KEY=pk_test_xxx
PAYSTACK_SECRET_KEY=sk_test_xxx
PAYSTACK_CURRENCY=NGN

# Resend Email (https://resend.com/api-keys)
RESEND_API_KEY=re_xxx
DEFAULT_FROM_EMAIL=FoodCourt <onboarding@resend.dev>

# Site URL (used in password reset links and emails)
SITE_URL=http://127.0.0.1:8000

# Django (optional — defaults provided for local dev)
SECRET_KEY=your-secret-key
DEBUG=True
```

### Resend Free Tier Note

The Resend free tier (`onboarding@resend.dev`) can only send to verified email addresses. In production, configure your own sending domain in the Resend dashboard.

---

## Deployment

### Render

The project is configured for deployment on Render:

1. Push to GitHub (`origin/main`)
2. Create a Render Web Service connected to the repo
3. Render runs `build.sh` which:
   - Installs dependencies from `requirements.txt`
   - Collects static files
   - Runs database migrations
   - Creates the default admin superuser
4. The app connects to a PostgreSQL database via `DATABASE_URL` environment variable

### Key Render Settings

| Setting | Value |
|---------|-------|
| Build Command | `./build.sh` |
| Start Command | (set in Render dashboard, typically `gunicorn Foodcourt.wsgi`) |
| Python Version | 3.12 |
| Environment | PostgreSQL via `dj-database-url` |

### Environment Variables for Render

Set these in the Render dashboard:

- `SECRET_KEY` — Django secret key
- `DEBUG` — Set to `False` in production
- `DATABASE_URL` — PostgreSQL connection string (auto-provided by Render)
- `RESEND_API_KEY` — Resend API key
- `DEFAULT_FROM_EMAIL` — Sender email address
- `SITE_URL` — Your production domain (e.g., `https://yourapp.onrender.com`)
- `PAYSTACK_PUBLIC_KEY` — Paystack public key
- `PAYSTACK_SECRET_KEY` — Paystack secret key
- `PAYSTACK_CURRENCY` — `NGN`

---

## User Roles

| Role | Registration | Dashboard | Key Capabilities |
|------|-------------|-----------|-----------------|
| **Customer** | `/register/` | `/dashboard/` | Browse restaurants, place orders, track deliveries, save addresses, rate riders |
| **Restaurant Owner** | `/restaurant/register/` | `/restaurant-admin/` | Manage menu, orders, categories, inventory, coupons, reviews, settings |
| **Rider** | `/riders/` | `/rider/dashboard/` | Accept deliveries, update status, OTP verification, earnings |
| **Admin** | Created via `python manage.py create_admin` | `/admin-dashboard/` | Platform management, user/rider oversight, delivery fee config, audit log |

---

## API Endpoints

### Public

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/api/locations/` | Countries, states, and LGAs for cascading dropdowns |
| GET | `/api/geocode/?q=` | Nominatim geocoding (fallback) |

### Authenticated Customer

| Method | URL | Purpose |
|--------|-----|---------|
| GET/POST | `/api/addresses/` | CRUD for delivery addresses |
| POST | `/api/delivery-fee/` | Calculate delivery fee (restaurant_id + address_id) |
| POST | `/api/profile/avatar/` | Upload profile picture |
| GET/POST | `/api/notifications/` | List and mark notifications as read |

### Restaurant Owner

| Method | URL | Purpose |
|--------|-----|---------|
| POST | `/restaurant-admin/api/` | 17 actions: order management, menu CRUD, categories, inventory, coupons, settings, reviews |

### Admin

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/admin-dashboard/` | Dashboard overview with stats |
| GET | `/admin-dashboard/restaurants/` | Restaurant management |
| POST | `/admin-dashboard/restaurants/<id>/update/` | Update restaurant details |
| POST | `/admin-dashboard/delivery-settings/` | Configure delivery fee tiers |
| POST | `/admin-dashboard/users/<id>/block/` | Block/unblock users |
| POST | `/admin-dashboard/riders/<id>/approve/` | Approve/reject riders |
| GET | `/admin-dashboard/export/users/` | Export users as CSV |
| GET | `/admin-dashboard/audit-log/` | View admin action audit log |

### Payments

| Method | URL | Purpose |
|--------|-----|---------|
| POST | `/payments/initialize/` | Initialize Paystack payment |
| GET | `/payments/verify/<ref>/` | Verify payment callback |
| GET | `/payments/result/` | Payment result page |
| GET | `/payments/receipt/<order_id>/` | Payment receipt |

---

## Payment Integration

FoodCourt uses [Paystack](https://paystack.com) for payment processing.

- **Currency**: Nigerian Naira (NGN)
- **Methods**: Card, Bank Transfer, USSD (via Paystack)
- **Cash on Delivery**: Also supported as an alternative
- **Flow**: Initialize payment → Redirect to Paystack → Callback verification → Order confirmation

The `Payment` model stores transaction references, status, and full gateway response for reconciliation.

---

## Email System

Transactional emails are sent via the [Resend](https://resend.com) API.

| Email | Trigger |
|-------|---------|
| Verification Code | New user or rider registration |
| Welcome Email | After successful verification |
| Password Reset | Forgot password request |
| Order Confirmation | After successful order placement |
| Restaurant Notification | New order received |
| Rider Welcome | New rider registration |
| Rider Approved | Admin approves rider |
| Rider Rejected | Admin rejects rider |

### Configuring Resend

1. Create an account at [resend.com](https://resend.com)
2. Get your API key from the dashboard
3. For production: add and verify your sending domain
4. For development: use `onboarding@resend.dev` (limited to verified recipients)

---

## Map & Location System

Location pinning uses two methods:

### 1. Use My Current Location
Uses the browser's Geolocation API to detect the user's coordinates.

### 2. Select Location on Map
An interactive Leaflet.js map with a draggable marker. Users click or drag to pin their exact location.

Both methods write latitude and longitude to hidden form fields. The user never sees raw coordinates.

### Map Provider
- **Library**: Leaflet.js 1.9.4 (CDN)
- **Tiles**: OpenStreetMap (free, no API key required)
- **Attribution**: Required by OSM tile usage policy (rendered automatically)

### Location Confirmation
- Each address/restaurant has a `location_confirmed` flag
- When address fields (State, LGA, Area, Street) change, coordinates are cleared and confirmation is reset
- The user must re-confirm the location after making address changes

---

## Delivery Fee Calculation

### Distance Calculation

1. **Primary**: OSRM (Open Source Routing Machine) for real road/route distance
2. **Fallback**: Haversine straight-line distance with a ×1.3 correction factor

### Fee Tiers (configurable via admin)

| Distance | Default Fee |
|----------|------------|
| 0–2 km | ₦700 |
| 2–5 km | ₦1,200 |
| 5–8 km | ₦1,700 |
| 8–12 km | ₦2,300 |
| 12–15 km | ₦3,000 |
| 15+ km | Outside delivery area |

### Architecture
- Coordinates are stored in the database (Restaurant + Address models)
- The backend fetches both sets of coordinates from the database — never trusts client-sent values for fee calculation
- Surge pricing multiplier is available (configurable in admin)

---

## User Roles — Dashboards

### Customer Dashboard (`/dashboard/`)
- Order history with status tracking
- Saved addresses with map-based location pinning
- Favorite restaurants

### Restaurant Dashboard (`/restaurant-admin/`)
- **Orders**: Accept, reject, update status (confirmed → preparing → ready)
- **Menu**: CRUD items with images, pricing, prep time
- **Categories**: Organize menu with emoji icons
- **Customers**: View order history per customer
- **Reviews**: Respond to and hide reviews
- **Inventory**: Track stock levels
- **Coupons**: Create and manage discount codes
- **Payments**: View payment history
- **Settings**: Restaurant profile, hours, delivery config, location

### Rider Dashboard (`/rider/dashboard/`)
- Online/offline toggle
- Available deliveries
- Active delivery management
- OTP verification for delivery completion
- Earnings and review history

### Admin Dashboard (`/admin-dashboard/`)
- Platform stats (users, orders, restaurants, riders)
- Restaurant management with location status
- User management (block, verify, delete)
- Rider approval workflow
- Delivery fee tier configuration
- Admin action audit log
- User data export

---

## License

This project is proprietary. All rights reserved.
