/* ============================================================
   Choply — Core App JS (Theme, Cart, Toast, Navbar, Reveals)
   ============================================================ */
'use strict';

/* ══════════════════════════════════════════════
   THEME MANAGER
══════════════════════════════════════════════ */
const ThemeManager = {
  key: 'foodcourt_theme',
  init() {
    const saved = localStorage.getItem(this.key) || 'light';
    this.apply(saved);
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
      btn.addEventListener('click', () => this.toggle());
    });
  },
  apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(this.key, theme);
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
      const icon = btn.querySelector('i');
      if (icon) {
        icon.className = theme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
      }
      btn.setAttribute('title', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    });
  },
  toggle() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    this.apply(current === 'dark' ? 'light' : 'dark');
  },
  isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }
};

/* ══════════════════════════════════════════════
   CART MANAGER
══════════════════════════════════════════════ */
const CartManager = {
  key: 'foodcourt_cart',

  getCart() {
    try { return JSON.parse(localStorage.getItem(this.key)) || []; }
    catch { return []; }
  },

  save(cart) {
    localStorage.setItem(this.key, JSON.stringify(cart));
    Navbar.updateCartBadge();
  },

  addItem(item) {
    const cart = this.getCart();
    const existing = cart.find(i => i.id === item.id);
    if (existing) {
      existing.qty = (existing.qty || 1) + 1;
    } else {
      cart.push({ ...item, qty: 1 });
    }
    this.save(cart);
    // Bump cart badge animation
    document.querySelectorAll('.cart-badge').forEach(b => {
      b.classList.remove('bump');
      void b.offsetWidth;
      b.classList.add('bump');
    });
    Toast.show(`${item.name} added to cart 🛒`, 'success');
    return cart;
  },

  removeItem(id) {
    const cart = this.getCart().filter(i => i.id !== id);
    this.save(cart);
    return cart;
  },

  updateQty(id, qty) {
    const cart = this.getCart();
    const item = cart.find(i => i.id === id);
    if (item) {
      if (qty <= 0) return this.removeItem(id);
      item.qty = qty;
      this.save(cart);
    }
    return this.getCart();
  },

  getTotal() {
    return this.getCart().reduce((sum, i) => sum + (i.price * (i.qty || 1)), 0);
  },

  getCount() {
    return this.getCart().reduce((sum, i) => sum + (i.qty || 1), 0);
  },

  clear() {
    localStorage.removeItem(this.key);
    Navbar.updateCartBadge();
  },

  getRestaurantId() {
    const cart = this.getCart();
    if (!cart.length) return null;
    return cart[0].restaurantId || null;
  }
};

/* ══════════════════════════════════════════════
   TOAST NOTIFICATIONS
══════════════════════════════════════════════ */
const Toast = {
  icons: {
    success: 'fa-solid fa-circle-check',
    error:   'fa-solid fa-circle-xmark',
    warning: 'fa-solid fa-triangle-exclamation',
    info:    'fa-solid fa-circle-info',
  },

  show(message, type = 'success', duration = 3000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `fc-toast ${type}`;
    toast.innerHTML = `
      <i class="fc-toast-icon ${this.icons[type] || this.icons.info}"></i>
      <span class="fc-toast-msg">${message}</span>
      <i class="fc-toast-close fa-solid fa-xmark" onclick="this.parentElement.remove()"></i>
    `;
    container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.classList.add('out');
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }
    return toast;
  }
};

/* ══════════════════════════════════════════════
   NAVBAR
══════════════════════════════════════════════ */
const Navbar = {
  init() {
    const navbar = document.querySelector('.fc-navbar');
    if (!navbar) return;

    // Scroll shadow
    const onScroll = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 20);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    this.updateCartBadge();
  },

  updateCartBadge() {
    const count = CartManager.getCount();
    document.querySelectorAll('.cart-badge').forEach(badge => {
      badge.textContent = count;
      badge.style.display = count > 0 ? 'flex' : 'none';
    });
  }
};

/* ══════════════════════════════════════════════
   FAVORITES
══════════════════════════════════════════════ */
const Favorites = {
  key: 'foodcourt_favorites',

  get() {
    try { return JSON.parse(localStorage.getItem(this.key)) || []; }
    catch { return []; }
  },

  toggle(restaurantId) {
    const favs = this.get();
    const id = Number(restaurantId);
    const idx = favs.indexOf(id);
    if (idx > -1) { favs.splice(idx, 1); }
    else { favs.push(id); }
    localStorage.setItem(this.key, JSON.stringify(favs));
    return this.isFavorite(id);
  },

  isFavorite(restaurantId) {
    return this.get().includes(Number(restaurantId));
  }
};

/* ══════════════════════════════════════════════
   SCROLL REVEAL (IntersectionObserver)
══════════════════════════════════════════════ */
const ScrollReveal = {
  init() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  }
};

/* ══════════════════════════════════════════════
   SKELETON LOADER
══════════════════════════════════════════════ */
const Skeleton = {
  restaurantCard() {
    return `
      <div class="fc-skeleton-card col">
        <div class="fc-skeleton fc-skeleton-img"></div>
        <div class="fc-skeleton-body">
          <div class="fc-skeleton fc-skeleton-line" style="width:75%"></div>
          <div class="fc-skeleton fc-skeleton-line short"></div>
          <div class="fc-skeleton fc-skeleton-line shorter"></div>
        </div>
      </div>`;
  },
  show(container, count = 6) {
    if (!container) return;
    container.innerHTML = Array(count).fill(this.restaurantCard()).join('');
  },
  hide(container) {
    if (!container) return;
    container.querySelectorAll('.fc-skeleton-card').forEach(el => el.remove());
  }
};

/* ══════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════ */
function renderStars(rating) {
  let html = '<span class="fc-stars">';
  for (let i = 1; i <= 5; i++) {
    if (i <= Math.floor(rating)) html += '<i class="fa-solid fa-star star filled"></i>';
    else if (i - 0.5 <= rating) html += '<i class="fa-solid fa-star-half-stroke star filled"></i>';
    else html += '<i class="fa-regular fa-star star"></i>';
  }
  html += '</span>';
  return html;
}

function formatPrice(p) { return '₦' + Number(p).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

function renderRestaurantCard(r) {
  const isFav = Favorites.isFavorite(r.id);
  return `
    <div class="col" onclick="window.location='/restaurant/${r.id}/'" style="cursor:pointer">
      <div class="fc-restaurant-card reveal">
        <div class="rc-img">
          <img src="${r.image}" alt="${r.name}" loading="lazy">
          <div class="rc-img-overlay"></div>
          <div class="rc-badges">
            ${r.isNew ? '<span class="fc-badge fc-badge-new"><i class="fa-solid fa-sparkles"></i> New</span>' : ''}
            ${r.isFeatured ? '<span class="fc-badge fc-badge-popular"><i class="fa-solid fa-fire"></i> Popular</span>' : ''}
            ${r.deliveryFee === 0 ? '<span class="fc-badge fc-badge-accent">Free Delivery</span>' : ''}
          </div>
          <button class="rc-fav-btn ${isFav ? 'active' : ''}" 
                  onclick="event.stopPropagation(); toggleFavoriteCard(this, ${r.id})"
                  aria-label="Toggle favourite">
            <i class="fa-${isFav ? 'solid' : 'regular'} fa-heart" style="color:${isFav ? '#FF4757' : '#6B7280'}"></i>
          </button>
          ${!r.isOpen ? '<div style="position:absolute;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;"><span class="fc-badge fc-badge-dark" style="font-size:14px">Closed</span></div>' : ''}
        </div>
        <div class="rc-body">
          <div class="rc-name">${r.name}</div>
          <div class="rc-cuisine">${r.cuisine}</div>
          <div class="rc-meta">
            <span class="rc-meta-item rc-rating">
              <i class="fa-solid fa-star" style="font-size:12px"></i>
              ${r.rating} <span style="color:var(--text-muted);font-weight:400">(${r.reviewCount.toLocaleString()})</span>
            </span>
            <span class="rc-meta-item">
              <i class="fa-regular fa-clock"></i> ${r.deliveryTime} min
            </span>
            <span class="rc-meta-item">
              <i class="fa-solid fa-motorcycle"></i>
              ${r.deliveryFee === 0 ? 'Free' : formatPrice(r.deliveryFee)}
            </span>
            <span class="rc-meta-item">
              <i class="fa-solid fa-bag-shopping"></i> Min ${formatPrice(r.minOrder)}
            </span>
          </div>
        </div>
      </div>
    </div>`;
}

function toggleFavoriteCard(btn, restaurantId) {
  const isFav = Favorites.toggle(restaurantId);
  btn.classList.toggle('active', isFav);
  const icon = btn.querySelector('i');
  if (icon) {
    icon.className = `fa-${isFav ? 'solid' : 'regular'} fa-heart`;
    icon.style.color = isFav ? '#FF4757' : '#6B7280';
    if (isFav) icon.style.animation = 'heartPop 0.35s var(--ease-spring)';
  }
  Toast.show(isFav ? 'Added to favourites ❤️' : 'Removed from favourites', isFav ? 'success' : 'info');
}

/* ══════════════════════════════════════════════
   URL PARAMS HELPER
══════════════════════════════════════════════ */
function getUrlParam(key) {
  return new URLSearchParams(window.location.search).get(key);
}

/* ══════════════════════════════════════════════
   INIT
══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
  Navbar.init();
  ScrollReveal.init();

  // Clear the cart when the user signs out
  document.addEventListener('click', (e) => {
    if (e.target.closest('a[href*="/logout/"]')) {
      CartManager.clear();
    }
  }, true);

  // Active nav link highlighting
  const path = window.location.pathname;
  document.querySelectorAll('.fc-navbar .nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href && (href === path || (href !== '/' && path.startsWith(href)))) {
      link.classList.add('active');
    }
  });
});

// Expose globally
window.ThemeManager = ThemeManager;
window.CartManager  = CartManager;
window.Toast        = Toast;
window.Navbar       = Navbar;
window.Favorites    = Favorites;
window.Skeleton     = Skeleton;
window.ScrollReveal = ScrollReveal;
window.renderStars         = renderStars;
window.formatPrice         = formatPrice;
window.renderRestaurantCard = renderRestaurantCard;
window.toggleFavoriteCard  = toggleFavoriteCard;
window.getUrlParam         = getUrlParam;
