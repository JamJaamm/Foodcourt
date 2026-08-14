/* ============================================================
   FoodCourt — Restaurant Detail Page JS (restaurant_detail.js)
   ============================================================ */
'use strict';

let currentRestaurant = null;
let currentMenu = [];
let currentReviews = [];

const DEFAULT_FOOD_IMG = 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&q=80';

function readJsonData(id) {
  const el = document.getElementById(id);
  if (!el || !el.textContent.trim()) return null;
  try { return JSON.parse(el.textContent); } catch (e) { return null; }
}

function getCookie(name) {
  let value = null;
  if (document.cookie && document.cookie !== '') {
    document.cookie.split(';').forEach(c => {
      c = c.trim();
      if (c.substring(0, name.length + 1) === (name + '=')) value = decodeURIComponent(c.substring(name.length + 1));
    });
  }
  return value;
}

document.addEventListener('DOMContentLoaded', () => {
  console.log("Restaurant Detail page loaded. Current Cart:", window.CartManager.getCart());
  // Parse Restaurant ID from pathname: e.g. /restaurant/1/
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  let restaurantId = Number(pathParts[pathParts.length - 1]);

  if (isNaN(restaurantId) || !window.FOODCOURT_DATA) {
    restaurantId = 1; // Default fallback to The Burger Lab
  }

  // Prefer real DB data injected by the Django view
  const dbRestaurant = readJsonData('db-restaurant-data');
  const dbMenu = readJsonData('db-menu-data');
  const dbReviews = readJsonData('db-reviews-data');

  if (dbRestaurant) {
    currentRestaurant = dbRestaurant;
  } else {
    currentRestaurant = window.FOODCOURT_DATA.restaurants.find(r => r.id === restaurantId);

    // Fallback if ID doesn't exist
    if (!currentRestaurant) {
      currentRestaurant = window.FOODCOURT_DATA.restaurants[0];
      restaurantId = currentRestaurant.id;
    }
  }

  // Get menu items (DB first, then static mock)
  if (dbMenu) {
    currentMenu = dbMenu;
  } else {
    currentMenu = window.FOODCOURT_DATA.menuItems[restaurantId] || window.FOODCOURT_DATA.menuItems[1];
  }

  currentReviews = dbReviews || (window.FOODCOURT_DATA ? window.FOODCOURT_DATA.testimonials : []);

  // Render operations
  renderRestaurantInfo();
  renderMenuTabs();
  renderMenuItems();
  renderReviews();
  renderReviewSummary();
  setupReviewForm();
  
  // Cart operations
  renderCartSidebar();

  // Scrollspy & Parallax
  setupTabScrollspy();
  window.addEventListener('scroll', handleParallax);
});

/* ══════════════════════════════════════════════
   RENDER RESTAURANT HEADER INFO
   ══════════════════════════════════════════════ */
function renderRestaurantInfo() {
  const r = currentRestaurant;
  if (!r) return;

  document.getElementById('rd-name').textContent = r.name;
  document.getElementById('rd-description').textContent = r.description;
  document.getElementById('rd-rating').textContent = r.rating.toFixed(1);
  document.getElementById('rd-reviews-count').textContent = `(${r.reviewCount.toLocaleString()} reviews)`;
  document.getElementById('rd-delivery-time').textContent = `${r.deliveryTime} min`;
  document.getElementById('rd-delivery-fee').textContent = r.deliveryFee === 0 ? 'Free delivery' : `Delivery: ${window.formatPrice(r.deliveryFee)}`;
  
  const statusEl = document.getElementById('rd-open-status');
  if (r.isOpen) {
    statusEl.innerHTML = `<i class="fa-solid fa-circle text-success" style="font-size:10px"></i> Open Now`;
  } else {
    statusEl.innerHTML = `<i class="fa-solid fa-circle text-danger" style="font-size:10px"></i> Closed`;
  }

  const heroImg = document.getElementById('rd-hero-img');
  if (heroImg) heroImg.src = r.image;
}

/* ══════════════════════════════════════════════
   RENDER TABS (Menu categories)
   ══════════════════════════════════════════════ */
function renderMenuTabs() {
  const container = document.getElementById('rd-menu-tabs-container');
  if (!container || !currentMenu) return;

  // Extract unique categories from the current restaurant's menu
  const categories = [...new Set(currentMenu.map(item => item.category))];

  if (categories.length === 0) return;

  container.innerHTML = categories.map((cat, idx) => `
    <button class="rd-tab-btn ${idx === 0 ? 'active' : ''}" 
            data-target="category-${cat.toLowerCase()}" 
            onclick="scrollToCategory(event, 'category-${cat.toLowerCase()}')">
      ${cat}
    </button>
  `).join('');
}

/* ══════════════════════════════════════════════
   RENDER MENU ITEMS
   ══════════════════════════════════════════════ */
function renderMenuItems() {
  const container = document.getElementById('menu-container');
  if (!container) return;

  if (!currentMenu || currentMenu.length === 0) {
    container.innerHTML = `
      <div class="text-center py-5">
        <div style="font-size:48px;margin-bottom:12px;">🍽️</div>
        <h4 class="fw-semibold">No menu items yet</h4>
        <p class="text-muted" style="max-width:360px;margin:0 auto;">This restaurant hasn't added any menu items yet. Check back soon!</p>
      </div>`;
    return;
  }

  // Group menu items by category
  const grouped = {};
  currentMenu.forEach(item => {
    if (!grouped[item.category]) grouped[item.category] = [];
    grouped[item.category].push(item);
  });

  const cart = window.CartManager.getCart();

  let html = '';
  for (const [category, items] of Object.entries(grouped)) {
    html += `
      <div class="rd-section" id="category-${category.toLowerCase()}">
        <h3 class="rd-section-title">${category}</h3>
        <div class="row row-cols-1 row-cols-md-2 g-4">
    `;

    items.forEach(item => {
      const cartItem = cart.find(ci => ci.id === item.id);
      const qtyInCart = cartItem ? cartItem.qty : 0;
      const imgSrc = item.image || DEFAULT_FOOD_IMG;

      html += `
        <div class="col">
          <div class="fc-food-card reveal">
            <img src="${imgSrc}" alt="${item.name}" class="fd-img" loading="lazy" onerror="this.src='${DEFAULT_FOOD_IMG}'">
            <div class="fd-body">
              <div>
                <div class="fd-header">
                  <div class="fd-name">${item.name}</div>
                  <div class="fd-price">${window.formatPrice(item.price)}</div>
                </div>
                <p class="fd-desc">${item.description}</p>
                <div class="fd-meta">
                  ${item.isVeg ? '<span class="text-success fw-bold"><i class="fa-solid fa-leaf"></i> Veg</span>' : ''}
                  ${item.isPopular ? '<span class="text-warning fw-bold"><i class="fa-solid fa-fire"></i> Popular</span>' : ''}
                  <span>🔥 ${item.calories} kcal</span>
                  <span>⏱️ ${item.prepTime}m</span>
                </div>
              </div>
              <div class="fd-actions">
                <!-- Inline Qty Picker or Add Button -->
                <div class="fc-qty-selector ${qtyInCart === 0 ? 'd-none' : ''}" id="qty-selector-${item.id}">
                  <button class="fc-qty-btn" onclick="updateItemQuantity(${item.id}, -1)">
                    <i class="fa-solid fa-minus"></i>
                  </button>
                  <span class="fc-qty-value" id="qty-value-${item.id}">${qtyInCart}</span>
                  <button class="fc-qty-btn" onclick="updateItemQuantity(${item.id}, 1)">
                    <i class="fa-solid fa-plus"></i>
                  </button>
                </div>
                <button class="fc-btn fc-btn-primary fc-btn-sm ${qtyInCart > 0 ? 'd-none' : ''}" 
                        id="add-btn-${item.id}"
                        onclick="addItemToCart(${item.id})">
                  <i class="fa-solid fa-plus me-1"></i> Add
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    });

    html += `
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
  
  if (window.ScrollReveal) {
    window.ScrollReveal.init();
  }
}

/* ══════════════════════════════════════════════
   RENDER REVIEWS COMMENT BLOCK
   ══════════════════════════════════════════════ */
function renderReviews() {
  const container = document.getElementById('reviews-comments-list');
  if (!container) return;

  if (!currentReviews || currentReviews.length === 0) {
    container.innerHTML = '<p class="text-muted text-center py-4">No reviews yet. Be the first to review this restaurant!</p>';
    return;
  }

  container.innerHTML = currentReviews.map(t => `
    <div class="rd-review-card reveal">
      <div class="rd-review-header">
        <div class="rd-review-user">
          <img src="${t.avatar}" alt="${t.name}" class="rd-review-avatar" loading="lazy">
          <div>
            <div class="rd-review-username">${t.name}</div>
            <div class="rd-review-date">${t.location} · ${t.date}</div>
          </div>
        </div>
        <div style="color:var(--warning);font-size:12px;">
          ${'★'.repeat(t.rating)}${'☆'.repeat(5 - t.rating)}
        </div>
      </div>
      <p class="rd-review-text">"${t.text}"</p>
      ${t.reply ? `
      <div class="rd-review-reply">
        <div class="rd-review-reply-head">
          <i class="fa-solid fa-store me-1 text-primary"></i><strong>Restaurant response</strong>
        </div>
        <p class="rd-review-reply-text">"${t.reply}"</p>
      </div>` : ''}
    </div>
  `).join('');
}

/* ══════════════════════════════════════════════
   SUBMIT REVIEW (STAR RATING) LOGIC
   ══════════════════════════════════════════════ */
let selectedReviewRating = 0;

const RATING_LABELS = {
  0: 'Tap a star to rate',
  1: 'Poor',
  2: 'Fair',
  3: 'Good',
  4: 'Very Good',
  5: 'Excellent'
};

function updateReviewLabel(val) {
  const labelEl = document.getElementById('rd-star-labels');
  if (!labelEl) return;
  labelEl.textContent = val > 0 ? `${RATING_LABELS[val]} (${val}/5)` : RATING_LABELS[0];
}

function setupReviewForm() {
  const commentEl = document.getElementById('review-comment');
  const counterEl = document.getElementById('rd-review-counter');
  if (commentEl && counterEl) {
    commentEl.addEventListener('input', () => {
      counterEl.textContent = `${commentEl.value.length}/500`;
    });
  }
}

window.setReviewRating = function(val) {
  selectedReviewRating = val;
  document.getElementById('review-rating').value = val;
  document.querySelectorAll('#rd-star-picker .rd-star').forEach(s => {
    s.classList.toggle('active', parseInt(s.dataset.val, 10) <= val);
  });
  updateReviewLabel(val);
};

function resetReviewForm() {
  selectedReviewRating = 0;
  const ratingEl = document.getElementById('review-rating');
  if (ratingEl) ratingEl.value = 0;
  document.querySelectorAll('#rd-star-picker .rd-star').forEach(s => s.classList.remove('active'));
  const commentEl = document.getElementById('review-comment');
  if (commentEl) commentEl.value = '';
  const counterEl = document.getElementById('rd-review-counter');
  if (counterEl) counterEl.textContent = '0/500';
  updateReviewLabel(0);
}

function renderReviewSummary() {
  const el = document.getElementById('reviews-summary-avg');
  if (el && currentRestaurant) el.textContent = currentRestaurant.rating.toFixed(1);
}

window.submitReview = function(e) {
  e.preventDefault();
  if (selectedReviewRating < 1) {
    window.Toast.show('Please select a star rating first', 'error');
    return;
  }
  if (!currentRestaurant) return;

  const comment = (document.getElementById('review-comment').value || '').trim();
  const form = document.getElementById('rd-review-form-card').querySelector('form');
  const btn = form.querySelector('button[type="submit"]');
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Submitting...';

  fetch(`/restaurant/${currentRestaurant.id}/review/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({ rating: selectedReviewRating, comment })
  })
  .then(r => r.json().then(d => ({ ok: r.ok, d })))
  .then(({ ok, d }) => {
    if (ok && d.success) {
      currentRestaurant.rating = d.rating;
      currentRestaurant.reviewCount = d.reviewCount;
      currentReviews = d.reviews;
      renderRestaurantInfo();
      renderReviewSummary();
      renderReviews();
      resetReviewForm();
      window.Toast.show('Review submitted! Thanks for your feedback.', 'success');
    } else {
      window.Toast.show(d.error || 'Failed to submit review', 'error');
    }
  })
  .catch(() => window.Toast.show('Failed to submit review', 'error'))
  .finally(() => {
    btn.disabled = false;
    btn.innerHTML = original;
  });
};

/* ══════════════════════════════════════════════
   CART SIDEBAR SYNC LOGIC
   ══════════════════════════════════════════════ */
function renderCartSidebar() {
  const container = document.getElementById('rd-cart-items-container');
  const emptyState = document.getElementById('rd-cart-empty-state');
  const nonemptyState = document.getElementById('rd-cart-nonempty-state');
  if (!container) return;

  const cart = window.CartManager.getCart();

  if (cart.length === 0) {
    emptyState.classList.remove('d-none');
    nonemptyState.classList.add('d-none');
    container.innerHTML = '';
    return;
  }

  emptyState.classList.add('d-none');
  nonemptyState.classList.remove('d-none');

  container.innerHTML = cart.map(item => `
    <div class="rd-cart-item">
      <div class="rd-ci-info">
        <div class="rd-ci-name">${item.name}</div>
        <div class="rd-ci-price">${window.formatPrice(item.price)}</div>
      </div>
      <div class="fc-qty-selector scale-90">
        <button class="fc-qty-btn" onclick="updateItemQuantity(${item.id}, -1)">
          <i class="fa-solid fa-minus" style="font-size:9px;"></i>
        </button>
        <span class="fc-qty-value">${item.qty}</span>
        <button class="fc-qty-btn" onclick="updateItemQuantity(${item.id}, 1)">
          <i class="fa-solid fa-plus" style="font-size:9px;"></i>
        </button>
      </div>
    </div>
  `).join('');

  // Update totals
  const subtotal = window.CartManager.getTotal();
  const delivery = currentRestaurant ? currentRestaurant.deliveryFee : 0;
  const total = subtotal + delivery;

  document.getElementById('rd-cart-subtotal').textContent = window.formatPrice(subtotal);
  document.getElementById('rd-cart-delivery').textContent = delivery === 0 ? 'Free' : window.formatPrice(delivery);
  document.getElementById('rd-cart-total').textContent = window.formatPrice(total);
}

/* ══════════════════════════════════════════════
   ADD TO CART HANDLER
   ══════════════════════════════════════════════ */
window.addItemToCart = function(itemId) {
  const menuItem = currentMenu.find(item => item.id === itemId);
  if (!menuItem) return;

  // Add via global CartManager
  window.CartManager.addItem({
    id: menuItem.id,
    name: menuItem.name,
    price: menuItem.price,
    image: menuItem.image,
    restaurantId: currentRestaurant.id
  });

  // Toggle button and input
  const addBtn = document.getElementById(`add-btn-${itemId}`);
  const qtySelector = document.getElementById(`qty-selector-${itemId}`);
  const qtyVal = document.getElementById(`qty-value-${itemId}`);

  if (addBtn && qtySelector && qtyVal) {
    addBtn.classList.add('d-none');
    qtySelector.classList.remove('d-none');
    qtyVal.textContent = 1;
  }

  renderCartSidebar();
};

/* ══════════════════════════════════════════════
   INCREMENT / DECREMENT QUANTITY
   ══════════════════════════════════════════════ */
window.updateItemQuantity = function(itemId, amount) {
  const cart = window.CartManager.getCart();
  const cartItem = cart.find(ci => ci.id === itemId);
  if (!cartItem) return;

  const newQty = cartItem.qty + amount;
  window.CartManager.updateQty(itemId, newQty);

  // Sync menu cards
  const qtyVal = document.getElementById(`qty-value-${itemId}`);
  const addBtn = document.getElementById(`add-btn-${itemId}`);
  const qtySelector = document.getElementById(`qty-selector-${itemId}`);

  if (newQty <= 0) {
    if (addBtn && qtySelector) {
      qtySelector.classList.add('d-none');
      addBtn.classList.remove('d-none');
    }
  } else {
    if (qtyVal) qtyVal.textContent = newQty;
  }

  // Refresh cart sidebar
  renderCartSidebar();
};

/* ══════════════════════════════════════════════
   NAVIGATION TAB SMOOTH SCROLL
   ══════════════════════════════════════════════ */
window.scrollToCategory = function(event, targetId) {
  event.preventDefault();
  const target = document.getElementById(targetId);
  if (!target) return;

  const headerOffset = varValue('--navbar-h') + 50;
  const elementPosition = target.getBoundingClientRect().top;
  const offsetPosition = elementPosition + window.scrollY - headerOffset;

  window.scrollTo({
    top: offsetPosition,
    behavior: 'smooth'
  });
};

/* ══════════════════════════════════════════════
   SCROLLSPY FOR CATEGORY SECTIONS
   ══════════════════════════════════════════════ */
function setupTabScrollspy() {
  const sections = document.querySelectorAll('.rd-section');
  const tabs = document.querySelectorAll('.rd-tab-btn');

  const onScroll = () => {
    let current = '';
    const scrollPos = window.scrollY + varValue('--navbar-h') + 120;

    sections.forEach(s => {
      const top = s.offsetTop;
      const height = s.offsetHeight;
      if (scrollPos >= top && scrollPos < top + height) {
        current = s.getAttribute('id');
      }
    });

    if (current) {
      tabs.forEach(tab => {
        tab.classList.toggle('active', tab.getAttribute('data-target') === current);
      });
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
}

/* ══════════════════════════════════════════════
   PARALLAX HERO ANIMATION
   ══════════════════════════════════════════════ */
function handleParallax() {
  const img = document.getElementById('rd-hero-img');
  if (!img) return;
  const scroll = window.scrollY;
  if (scroll < 400) {
    img.style.transform = `scale(1.05) translateY(${scroll * 0.4}px)`;
  }
}

/* ── Utility: get CSS variable number ── */
function varValue(name) {
  const val = getComputedStyle(document.documentElement).getPropertyValue(name);
  return parseInt(val, 10) || 0;
}
