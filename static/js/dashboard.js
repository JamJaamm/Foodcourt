/* ============================================================
   FoodCourt — User Dashboard Page JS (dashboard.js)
   ============================================================ */
'use strict';

let customAddresses = [];

function readJsonData(id) {
  const el = document.getElementById(id);
  if (!el || !el.textContent.trim()) return null;
  try { return JSON.parse(el.textContent); } catch (e) { return null; }
}

document.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash.replace('#', '');
  if (hash) {
    switchDashboardTab(hash);
  } else {
    switchDashboardTab('overview');
  }

  renderPastOrders();
  loadAddresses();
  renderFavorites();
});

/* ══════════════════════════════════════════════
   TAB SWITCHING LOGIC (HASH DRIVEN)
   ══════════════════════════════════════════════ */
window.switchDashboardTab = function(tabId) {
  const tabs = ['overview', 'orders', 'addresses', 'favorites', 'settings'];
  if (!tabs.includes(tabId)) return;

  // Toggle buttons
  tabs.forEach(t => {
    const btn = document.getElementById(`db-btn-${t}`);
    const panel = document.getElementById(`db-tab-${t}`);
    
    if (btn) btn.classList.toggle('active', t === tabId);
    if (panel) panel.classList.toggle('active', t === tabId);
  });

  // Update hash safely
  window.location.hash = tabId;

  // Re-render favorites in case they changed on other pages
  if (tabId === 'favorites') {
    renderFavorites();
  }
};

/* ══════════════════════════════════════════════
   RENDER PAST ORDERS
   ══════════════════════════════════════════════ */
function renderPastOrders() {
  const recentContainer = document.getElementById('db-recent-orders-list');
  const fullContainer = document.getElementById('db-full-orders-list');
  if (!recentContainer || !fullContainer) return;

  const orders = readJsonData('db-user-orders') || window.FOODCOURT_USER_ORDERS || [];

  const getBadgeClass = (status) => {
    const s = status.toLowerCase();
    if (s === 'delivered') return 'fc-badge-accent';
    if (s === 'cancelled') return 'fc-badge-dark';
    return 'fc-badge-popular';
  };

  const renderOrderHtml = (o, idx) => `
    <div class="db-order-row reveal stagger-${(idx % 4) + 1}">
      <div class="db-order-info">
        <img src="${o.restaurantImage || 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=100&q=80'}" alt="${o.restaurantName}" class="db-order-img" loading="lazy">
        <div>
          <div class="db-order-name">${o.restaurantName}</div>
          <div class="db-order-date">${o.date} · ${o.items.length} items · <strong>${window.formatPrice(o.total)}</strong></div>
        </div>
      </div>
      
      <div class="d-flex align-items-center gap-2 mt-2 mt-sm-0">
        <span class="fc-badge ${getBadgeClass(o.status)}" style="font-size:12px;">${o.status}</span>
        <button class="fc-btn fc-btn-outline fc-btn-sm py-2" onclick="window.location.href='/tracking/${o.id}/'">
          <i class="fa-solid fa-location-dot me-1"></i> Track
        </button>
        <button class="fc-btn fc-btn-outline fc-btn-sm py-2" onclick="reorderItems(${JSON.stringify(o.items).replace(/"/g, '&quot;')})">
          <i class="fa-solid fa-rotate-right me-1"></i> Reorder
        </button>
      </div>
    </div>
  `;

  recentContainer.innerHTML = orders.length > 0
    ? orders.slice(0, 3).map((o, idx) => renderOrderHtml(o, idx)).join('')
    : '<div class="text-center py-4 text-muted" style="font-size:13px;">No recent orders yet. <a href="/restaurants/" class="text-primary fw-bold">Start ordering!</a></div>';
  fullContainer.innerHTML = orders.length > 0 ? orders.map((o, idx) => renderOrderHtml(o, idx)).join('') : '<div class="text-center py-5 text-muted" style="font-size:14px;">No orders yet. <a href="/restaurants/" class="text-primary fw-bold">Start ordering!</a></div>';

  if (window.ScrollReveal) window.ScrollReveal.init();
}

/* ══════════════════════════════════════════════
   REORDER ACTION HANDLER
   ══════════════════════════════════════════════ */
window.reorderItems = function(itemsArray) {
  if (!itemsArray || itemsArray.length === 0) return;

  itemsArray.forEach(item => {
    // Re-use core app CartManager to inject item row into local storage cart list
    window.CartManager.addItem({
      id: Math.floor(Math.random() * 10000), // assign new temporary item ID
      name: item.name,
      price: item.price,
      // fallback sample placeholder Unsplash food photo url
      image: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=100&q=80'
    });
  });

  Toast.show('All items added to cart! Redirecting...', 'success');
  
  setTimeout(() => {
    window.location.href = '/cart/';
  }, 1000);
};

/* ══════════════════════════════════════════════
   RENDER SAVED ADDRESSES
   ══════════════════════════════════════════════ */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function loadAddresses() {
  const inline = readJsonData('db-user-addresses');
  if (inline) {
    window.FOODCOURT_USER_ADDRESSES = inline;
    renderAddresses();
  }
  fetch('/api/addresses/')
    .then(r => r.json())
    .then(data => {
      window.FOODCOURT_USER_ADDRESSES = data.addresses || [];
      renderAddresses();
    })
    .catch(() => {});
}

function renderAddresses() {
  const container = document.getElementById('db-addresses-list');
  if (!container) return;

  const list = window.FOODCOURT_USER_ADDRESSES || [];

  if (list.length === 0) {
    container.innerHTML = `
      <div class="col-12 text-center py-5 text-muted" style="font-size:14px;">
        <div style="font-size:36px;margin-bottom:8px">🏠</div>
        <p class="fw-semibold">No saved addresses yet</p>
        <button class="fc-btn fc-btn-primary fc-btn-sm mt-2" onclick="toggleAddAddressForm()">Add New Address</button>
      </div>
    `;
    if (window.ScrollReveal) window.ScrollReveal.init();
    return;
  }

  container.innerHTML = list.map(addr => {
    const icon = addr.label && addr.label.toLowerCase().includes('work') ? 'fa-building' : 'fa-house';
    const landmarkHtml = addr.landmark ? `<div class="addr-detail-line"><i class="fa-solid fa-location-dot"></i><span>Near ${addr.landmark}</span></div>` : '';
    const cityState = [addr.city, addr.state].filter(Boolean).join(', ');
    const countryHtml = addr.country ? `<div class="addr-detail-line"><i class="fa-solid fa-globe"></i><span>${addr.country}</span></div>` : '';
    const phoneHtml = addr.phone ? `<div class="addr-detail-line"><i class="fa-solid fa-phone"></i><span>${addr.phone}</span></div>` : '';
    return `
    <div class="db-address-card reveal" id="db-addr-${addr.id}">
      <div class="db-address-header">
        <span class="db-address-label">
          <i class="fa-solid ${icon} text-primary"></i> ${addr.label}
          ${addr.is_default ? '<span class="fc-badge fc-badge-accent text-xxs scale-90" style="padding:1px 6px;">Default</span>' : ''}
        </span>
      </div>
      <div class="addr-detail-line"><i class="fa-solid fa-house"></i><span>${addr.street}</span></div>
      ${landmarkHtml}
      <div class="addr-detail-line"><i class="fa-solid fa-city"></i><span>${cityState || addr.city}</span></div>
      ${countryHtml}
      ${phoneHtml}
      
      <div class="db-address-actions">
        <button class="db-address-btn edit" onclick="editAddressCard(${addr.id})">
          <i class="fa-solid fa-pen-to-square"></i> Edit
        </button>
        <button class="db-address-btn delete" onclick="deleteAddressCard(${addr.id})">
          <i class="fa-solid fa-trash-can"></i> Delete
        </button>
      </div>
    </div>
  `}).join('');

  if (window.ScrollReveal) window.ScrollReveal.init();
}

window.toggleAddAddressForm = function() {
  const card = document.getElementById('add-address-form-card');
  if (card) card.classList.toggle('d-none');
};

window.saveNewAddress = function(event) {
  event.preventDefault();

  const data = {
    action: 'create',
    label: document.getElementById('new-addr-label').value,
    street: document.getElementById('new-addr-street').value.trim(),
    landmark: document.getElementById('new-addr-landmark').value.trim(),
    city: document.getElementById('new-addr-city').value.trim(),
    state: document.getElementById('new-addr-state').value.trim(),
    country: document.getElementById('new-addr-country').value.trim(),
    phone: document.getElementById('new-addr-phone').value.trim(),
  };
  if (!data.label || !data.street) { Toast.show('Label and street address are required', 'error'); return; }

  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Saving...';

  const csrfToken = getCookie('csrftoken');
  fetch('/api/addresses/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify(data)
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      document.getElementById('new-addr-label').value = '';
      document.getElementById('new-addr-street').value = '';
      document.getElementById('new-addr-landmark').value = '';
      document.getElementById('new-addr-city').value = '';
      populateStates(document.getElementById('new-addr-country').value, document.getElementById('new-addr-state'), '');
      document.getElementById('new-addr-phone').value = '';
      toggleAddAddressForm();
      loadAddresses();
      Toast.show('Address saved!', 'success');
    } else {
      Toast.show(res.error || 'Failed to save', 'error');
    }
  })
  .catch(() => Toast.show('Failed to save address', 'error'))
  .finally(() => {
    btn.disabled = false;
    btn.innerHTML = orig;
  });
};

window.editAddressCard = function(id) {
  const list = window.FOODCOURT_USER_ADDRESSES || [];
  const addr = list.find(a => a.id === id);
  if (!addr) return;

  document.getElementById('edit-addr-id').value = addr.id;
  document.getElementById('edit-addr-label').value = addr.label;
  document.getElementById('edit-addr-street').value = addr.street || '';
  document.getElementById('edit-addr-landmark').value = addr.landmark || '';
  document.getElementById('edit-addr-city').value = addr.city || '';
  document.getElementById('edit-addr-country').value = addr.country || '';
  populateStates(addr.country || '', document.getElementById('edit-addr-state'), addr.state || '');
  document.getElementById('edit-addr-phone').value = addr.phone || '';

  const card = document.getElementById('edit-address-form-card');
  card.classList.remove('d-none');
  card.scrollIntoView({ behavior: 'smooth', block: 'center' });
};

window.toggleEditAddressForm = function() {
  const card = document.getElementById('edit-address-form-card');
  if (card) card.classList.toggle('d-none');
};

window.saveEditAddress = function(event) {
  event.preventDefault();

  const id = document.getElementById('edit-addr-id').value;
  const data = {
    action: 'update',
    id: parseInt(id),
    label: document.getElementById('edit-addr-label').value,
    street: document.getElementById('edit-addr-street').value.trim(),
    landmark: document.getElementById('edit-addr-landmark').value.trim(),
    city: document.getElementById('edit-addr-city').value.trim(),
    state: document.getElementById('edit-addr-state').value.trim(),
    country: document.getElementById('edit-addr-country').value.trim(),
    phone: document.getElementById('edit-addr-phone').value.trim(),
  };
  if (!data.label || !data.street || !id) { Toast.show('Label and street address are required', 'error'); return; }

  const btn = event.target.querySelector('button[type="submit"]');
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Saving...';

  const csrfToken = getCookie('csrftoken');
  fetch('/api/addresses/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify(data)
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      toggleEditAddressForm();
      loadAddresses();
      Toast.show('Address updated!', 'success');
    } else {
      Toast.show(res.error || 'Failed to update', 'error');
    }
  })
  .catch(() => Toast.show('Failed to update address', 'error'))
  .finally(() => {
    btn.disabled = false;
    btn.innerHTML = orig;
  });
};

window.deleteAddressCard = function(id) {
  const card = document.getElementById(`db-addr-${id}`);
  if (!card) return;

  if (!confirm('Delete this address?')) return;

  card.style.transform = 'scale(0.9)';
  card.style.opacity = '0';

  const csrfToken = getCookie('csrftoken');
  fetch('/api/addresses/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ action: 'delete', id: id })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      loadAddresses();
      Toast.show('Address deleted', 'info');
    } else {
      Toast.show(data.error || 'Failed to delete', 'error');
      renderAddresses();
    }
  })
  .catch(() => {
    Toast.show('Failed to delete', 'error');
    renderAddresses();
  });
};

/* ══════════════════════════════════════════════
   RENDER FAVORITE RESTAURANTS
   ══════════════════════════════════════════════ */
function renderFavorites() {
  const container = document.getElementById('db-favorites-grid');
  if (!container) return;

  const favIds = window.Favorites ? window.Favorites.get() : [];
  const dbRestaurants = readJsonData('db-restaurants-data') || [];

  let list = dbRestaurants.filter(r => favIds.includes(r.id));

  // Fallback to mock restaurants (e.g. favorited on the mock-driven homepage)
  if (list.length === 0 && window.FOODCOURT_DATA) {
    const dbIds = new Set(dbRestaurants.map(r => r.id));
    const mockOnly = window.FOODCOURT_DATA.restaurants.filter(r => !dbIds.has(r.id) && favIds.includes(r.id));
    list = mockOnly;
  }

  if (list.length === 0) {
    container.innerHTML = `
      <div class="col-12 text-center py-5 text-muted" style="font-size:14px">
        <div style="font-size:36px;margin-bottom:8px">❤️</div>
        <p class="fw-semibold">No favorite restaurants added yet</p>
        <a href="/restaurants/" class="fc-btn fc-btn-primary fc-btn-sm mt-2">Explore Restaurants</a>
      </div>
    `;
    return;
  }

  // Render cards columns
  container.innerHTML = list.map((r, idx) => {
    const cardHtml = window.renderRestaurantCard(r);
    // Style override card for responsive columns size inside workspace container
    return cardHtml.replace('col', `col-md-6 col-xxl-4 stagger-${(idx % 4) + 1}`);
  }).join('');

  if (window.ScrollReveal) {
    window.ScrollReveal.init();
  }
}

/* ══════════════════════════════════════════════
   AVATAR UPLOAD
   ══════════════════════════════════════════════ */
function syncAvatarImg(url) {
  ['db-avatar-preview', 'db-settings-avatar'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.onerror = null;
    el.style.display = '';
    el.src = url;
    const fallback = document.getElementById(id === 'db-avatar-preview' ? 'db-avatar-fallback' : 'db-settings-avatar-fallback');
    if (fallback) fallback.style.display = 'none';
  });
}

function uploadAvatarFile(file) {
  const csrfToken = getCookie('csrftoken');
  const fd = new FormData();
  fd.append('avatar_file', file);

  return fetch('/api/profile/avatar/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    body: fd
  })
  .then(r => r.json())
  .then(res => {
    if (res.success && res.avatar) {
      syncAvatarImg(res.avatar);
      Toast.show('Profile picture updated!', 'success');
      return true;
    }
    Toast.show(res.error || 'Failed to upload picture', 'error');
    return false;
  })
  .catch(() => {
    Toast.show('Failed to upload picture', 'error');
    return false;
  });
}

window.previewDashboardAvatar = function(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  const avatarEl = document.getElementById('db-avatar-preview');

  const reader = new FileReader();
  reader.onload = function(e) {
    if (avatarEl) avatarEl.src = e.target.result;
  };
  reader.readAsDataURL(file);

  uploadAvatarFile(file).finally(() => { input.value = ''; });
};

window.changeSettingsAvatar = function(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  const avatarEl = document.getElementById('db-settings-avatar');

  const reader = new FileReader();
  reader.onload = function(e) {
    if (avatarEl) avatarEl.src = e.target.result;
  };
  reader.readAsDataURL(file);

  uploadAvatarFile(file).finally(() => { input.value = ''; });
};

/* ══════════════════════════════════════════════
   SETTINGS FORM SAVE
   ══════════════════════════════════════════════ */
window.saveProfileSettings = function(event) {
  event.preventDefault();

  const fname = document.getElementById('db-settings-fname').value.trim();
  const lname = document.getElementById('db-settings-lname').value.trim();
  const email = document.getElementById('db-settings-email').value.trim();

  // Update header labels
  document.getElementById('db-profile-name').textContent = `${fname} ${lname}`;
  document.getElementById('db-profile-email').textContent = email;

  // Mock submit spinner
  const submitBtn = event.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin me-1"></i> Saving...`;

  setTimeout(() => {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
    Toast.show('Profile updated successfully! ✅', 'success');
  }, 1000);
};
