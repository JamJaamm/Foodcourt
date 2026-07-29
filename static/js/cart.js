'use strict';

let currentAddressId = 1;
let currentPaymentMethod = 'card';
let appliedPromo = null;

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

document.addEventListener('DOMContentLoaded', () => {
  console.log("Cart/Checkout Page loaded. Current Cart:", window.CartManager.getCart());
  renderCartItems();
  renderSavedAddresses();
  setupInputFormatting();
});


function renderCartItems() {
  const container = document.getElementById('checkout-items-list');
  const emptyView = document.getElementById('cart-empty-view');
  const nonemptyView = document.getElementById('cart-nonempty-view');
  if (!container) return;

  const cart = window.CartManager.getCart();

  if (cart.length === 0) {
    emptyView.classList.remove('d-none');
    nonemptyView.classList.add('d-none');
    return;
  }

  emptyView.classList.add('d-none');
  nonemptyView.classList.remove('d-none');

  container.innerHTML = cart.map(item => `
    <div class="checkout-item-row">
      <img src="${item.image}" alt="${item.name}" class="checkout-item-img" loading="lazy">
      <div class="checkout-item-details">
        <div class="checkout-item-name">${item.name}</div>
        <div class="checkout-item-price">
          ${item.qty} × ${window.formatPrice(item.price)} = <strong>${window.formatPrice(item.price * item.qty)}</strong>
        </div>
      </div>
      <div class="fc-qty-selector scale-90 mx-3">
        <button class="fc-qty-btn" onclick="adjustItemQty(${item.id}, -1)">
          <i class="fa-solid fa-minus" style="font-size:9px;"></i>
        </button>
        <span class="fc-qty-value">${item.qty}</span>
        <button class="fc-qty-btn" onclick="adjustItemQty(${item.id}, 1)">
          <i class="fa-solid fa-plus" style="font-size:9px;"></i>
        </button>
      </div>
      <button class="checkout-item-remove" onclick="removeCheckoutItem(${item.id})" aria-label="Remove item">
        <i class="fa-solid fa-trash-can"></i>
      </button>
    </div>
  `).join('');
  if (window.ScrollReveal) {
    window.ScrollReveal.init();
  }

  updateCheckoutTotals();
}

window.adjustItemQty = function(itemId, amount) {
  const cart = window.CartManager.getCart();
  const item = cart.find(ci => ci.id === itemId);
  if (!item) return;

  const newQty = item.qty + amount;
  window.CartManager.updateQty(itemId, newQty);
  renderCartItems();
};

window.removeCheckoutItem = function(itemId) {
  window.CartManager.removeItem(itemId);
  renderCartItems();
  Toast.show('Item removed from cart', 'info');
};

window.clearFullCart = function() {
  if (confirm('Are you sure you want to clear your entire cart?')) {
    window.CartManager.clear();
    renderCartItems();
    Toast.show('Cart cleared completely 🧹', 'info');
  }
};

/* ══════════════════════════════════════════════
   UPDATE TOTAL BREAKDOWN
   ══════════════════════════════════════════════ */
function updateCheckoutTotals() {
  const subtotal = window.CartManager.getTotal();
  
  // Custom delivery fee (e.g. $2.99 or free if subtotal > $30 or promo applied)
  let deliveryFee = subtotal > 30 ? 0 : 2.99;
  let discount = 0;

  if (appliedPromo) {
    if (appliedPromo.type === 'percent') {
      discount = subtotal * (appliedPromo.value / 100);
    } else if (appliedPromo.type === 'fixed') {
      discount = appliedPromo.value;
    } else if (appliedPromo.type === 'delivery') {
      deliveryFee = 0;
    }
  }

  // Ensure discount doesn't exceed subtotal
  if (discount > subtotal) discount = subtotal;

  const grandTotal = Math.max(0, subtotal + deliveryFee - discount);

  document.getElementById('checkout-subtotal').textContent = window.formatPrice(subtotal);
  document.getElementById('checkout-delivery').textContent = deliveryFee === 0 ? 'Free' : window.formatPrice(deliveryFee);
  
  const discountRow = document.getElementById('discount-row');
  if (discount > 0 || (appliedPromo && appliedPromo.type === 'delivery')) {
    discountRow.classList.remove('d-none');
    document.getElementById('discount-code-label').textContent = appliedPromo.code;
    document.getElementById('checkout-discount').textContent = `-${window.formatPrice(discount)}`;
  } else {
    discountRow.classList.add('d-none');
  }

  document.getElementById('checkout-total').textContent = window.formatPrice(grandTotal);
  document.getElementById('btn-total-label').textContent = window.formatPrice(grandTotal);
}

/* ══════════════════════════════════════════════
   PROMO CODE ACTIONS
   ══════════════════════════════════════════════ */
window.applyPromoCode = function() {
  const input = document.getElementById('promo-code-input');
  const msgEl = document.getElementById('promo-feedback-message');
  if (!input || !msgEl || !window.FOODCOURT_DATA) return;

  const code = input.value.trim().toUpperCase();
  msgEl.className = 'promo-feedback';

  if (!code) {
    msgEl.textContent = 'Please enter a promo code.';
    msgEl.classList.add('error');
    return;
  }

  const promo = window.FOODCOURT_DATA.promoCodes[code];

  if (promo) {
    appliedPromo = { ...promo, code: code };
    msgEl.textContent = `Promo code "${code}" applied successfully! (${promo.label})`;
    msgEl.classList.add('success');
    updateCheckoutTotals();
    Toast.show('Promo applied! 🎟️', 'success');
  } else {
    appliedPromo = null;
    msgEl.textContent = 'Invalid promo code. Try SAVE10, FIRST20, FREESHIP.';
    msgEl.classList.add('error');
    updateCheckoutTotals();
  }
};

/* ══════════════════════════════════════════════
   RENDER SAVED ADDRESSES
   ══════════════════════════════════════════════ */
function renderSavedAddresses() {
  const container = document.getElementById('saved-addresses-container');
  if (!container) return;

  const list = window.FOODCOURT_USER_ADDRESSES || (window.FOODCOURT_DATA && window.FOODCOURT_DATA.addresses) || [];
  container.innerHTML = list.map(addr => {
    const isActive = addr.id === currentAddressId;
    const icon = addr.label && addr.label.toLowerCase().includes('work') ? 'fa-building' : 'fa-house';
    return `
      <div class="address-option-card ${isActive ? 'active' : ''}" 
           onclick="selectAddressCard(${addr.id})"
           id="address-card-${addr.id}">
        <input type="radio" name="saved-address-radio" class="address-option-radio" ${isActive ? 'checked' : ''}>
        <div>
          <strong style="color:var(--text-primary)"><i class="fa-solid ${icon} me-1"></i> ${addr.label}</strong>
          <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${addr.address}</div>
        </div>
      </div>
    `;
  }).join('');
}

window.selectAddressCard = function(id) {
  currentAddressId = id;
  
  // UI classes toggle
  document.querySelectorAll('.address-option-card').forEach(card => {
    const isTarget = card.id === `address-card-${id}`;
    card.classList.toggle('active', isTarget);
    const radio = card.querySelector('.address-option-radio');
    if (radio) radio.checked = isTarget;
  });

  // Clear manual input if they click saved
  const manual = document.getElementById('delivery-address-manual');
  if (manual) manual.value = '';
};

/* ══════════════════════════════════════════════
   DELIVERY TIME SCHEDULE TOGGLE
   ══════════════════════════════════════════════ */
window.toggleScheduledTime = function(select) {
  const wrap = document.getElementById('scheduled-time-wrap');
  if (!wrap) return;
  if (select.value === 'schedule') {
    wrap.classList.remove('d-none');
    // Set default schedule time 1 hour from now
    const now = new Date();
    now.setHours(now.getHours() + 1);
    document.getElementById('delivery-time-picker').value = now.toISOString().slice(0, 16);
  } else {
    wrap.classList.add('d-none');
  }
};

/* ══════════════════════════════════════════════
   PAYMENT SWITCHER
   ══════════════════════════════════════════════ */
window.switchPaymentMethod = function(method) {
  currentPaymentMethod = method;

  // Toggle active tab class
  document.querySelectorAll('.payment-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.id === `pay-tab-${method}`);
  });

  // Show/Hide details rows
  document.getElementById('payment-card-details').classList.toggle('d-none', method !== 'card');
  document.getElementById('payment-cash-details').classList.toggle('d-none', method !== 'cash');
  document.getElementById('payment-wallet-details').classList.toggle('d-none', method !== 'wallet');
};

/* ══════════════════════════════════════════════
   INPUT FORMATTERS
   ══════════════════════════════════════════════ */
function setupInputFormatting() {
  const ccNum = document.getElementById('cc-number');
  const ccExp = document.getElementById('cc-expiry');
  const ccCvv = document.getElementById('cc-cvv');

  if (ccNum) {
    ccNum.addEventListener('input', (e) => {
      // Formats: xxxx xxxx xxxx xxxx
      let val = e.target.value.replace(/\D/g, '');
      let formatted = '';
      for (let i = 0; i < val.length; i++) {
        if (i > 0 && i % 4 === 0) formatted += ' ';
        formatted += val[i];
      }
      e.target.value = formatted.slice(0, 19);
    });
  }

  if (ccExp) {
    ccExp.addEventListener('input', (e) => {
      // Formats: MM/YY
      let val = e.target.value.replace(/\D/g, '');
      if (val.length >= 2) {
        e.target.value = val.slice(0, 2) + '/' + val.slice(2, 4);
      } else {
        e.target.value = val;
      }
    });
  }

  if (ccCvv) {
    ccCvv.addEventListener('input', (e) => {
      e.target.value = e.target.value.replace(/\D/g, '').slice(0, 3);
    });
  }
}

/* ══════════════════════════════════════════════
   ORDER SUBMISSION FLOW
   ══════════════════════════════════════════════ */
window.submitOrder = function() {
  const cart = window.CartManager.getCart();
  if (cart.length === 0) {
    Toast.show('Cart is empty', 'error');
    return;
  }

  if (!window.FOODCOURT_USER || !window.FOODCOURT_USER.isAuthenticated) {
    Toast.show('Please sign in to place an order', 'error');
    setTimeout(() => window.location.href = '/login/', 1500);
    return;
  }

  const manualAddressInput = document.getElementById('delivery-address-manual');
  let finalAddress = '';
  if (currentAddressId !== null) {
    const addressList = window.FOODCOURT_USER_ADDRESSES || (window.FOODCOURT_DATA && window.FOODCOURT_DATA.addresses) || [];
    const saved = addressList.find(a => a.id === currentAddressId);
    finalAddress = saved ? saved.address : '';
  } else {
    finalAddress = manualAddressInput ? manualAddressInput.value.trim() : '';
  }

  if (!finalAddress) {
    Toast.show('Please select a saved address or enter a delivery address.', 'error');
    return;
  }

  if (currentPaymentMethod === 'card') {
    const ccNum = document.getElementById('cc-number').value.trim();
    const ccExp = document.getElementById('cc-expiry').value.trim();
    const ccCvv = document.getElementById('cc-cvv').value.trim();
    if (ccNum.length < 15 || ccExp.length < 5 || ccCvv.length < 3) {
      Toast.show('Please enter valid credit card details.', 'error');
      document.getElementById('payment-card-details').classList.add('animate-wiggle');
      setTimeout(() => {
        document.getElementById('payment-card-details').classList.remove('animate-wiggle');
      }, 500);
      return;
    }
  }

  const firstItem = cart[0];
  let restaurantName = 'FoodCourt Order';
  if (firstItem.restaurantId && window.FOODCOURT_DATA && window.FOODCOURT_DATA.restaurants) {
    const rest = window.FOODCOURT_DATA.restaurants.find(r => r.id === firstItem.restaurantId);
    if (rest) restaurantName = rest.name;
  }

  const subtotal = window.CartManager.getTotal();
  let deliveryFee = subtotal > 30 ? 0 : 2.99;
  let discount = 0;
  if (appliedPromo) {
    if (appliedPromo.type === 'percent') discount = subtotal * (appliedPromo.value / 100);
    else if (appliedPromo.type === 'fixed') discount = appliedPromo.value;
    else if (appliedPromo.type === 'delivery') deliveryFee = 0;
  }
  if (discount > subtotal) discount = subtotal;
  const grandTotal = Math.max(0, subtotal + deliveryFee - discount);

  const orderBtn = document.getElementById('place-order-btn');
  const originalText = orderBtn.innerHTML;
  orderBtn.disabled = true;
  orderBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Placing Order...';

  const orderData = {
    items: cart.map(item => ({
      name: item.name,
      price: item.price,
      qty: item.qty,
      image: item.image || ''
    })),
    delivery_address: finalAddress,
    payment_method: currentPaymentMethod,
    subtotal: subtotal,
    delivery_fee: deliveryFee,
    discount: discount,
    total: grandTotal,
    restaurant_name: restaurantName
  };

  const csrfToken = getCookie('csrftoken');

  fetch('/order/place/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(orderData)
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(err => { throw new Error(err.error || 'Failed to place order'); });
    }
    return response.json();
  })
  .then(data => {
    localStorage.setItem('foodcourt_active_order_id', data.order_id);
    localStorage.setItem('foodcourt_active_order_address', finalAddress);
    localStorage.setItem('foodcourt_active_order_total', window.formatPrice(grandTotal));

    window.CartManager.clear();

    orderBtn.disabled = false;
    orderBtn.innerHTML = originalText;

    document.getElementById('success-order-id').textContent = data.order_id;
    const overlay = document.getElementById('checkout-success-overlay');
    overlay.classList.add('show');
    triggerSuccessConfetti();
    Toast.show('Order placed successfully! 🍕', 'success');
  })
  .catch(error => {
    orderBtn.disabled = false;
    orderBtn.innerHTML = originalText;
    Toast.show(error.message || 'Failed to place order', 'error');
  });
};

/* ══════════════════════════════════════════════
   CONFETTI CELEBRATION
   ══════════════════════════════════════════════ */
function triggerSuccessConfetti() {
  const overlay = document.getElementById('checkout-success-overlay');
  if (!overlay) return;

  const colors = ['#FF6B35', '#FF8C42', '#06D6A0', '#FFB800', '#FF4757', '#2ED573'];
  const particleCount = 45;

  for (let i = 0; i < particleCount; i++) {
    const particle = document.createElement('div');
    particle.className = 'confetti-particle';
    
    // Style settings
    particle.style.background = colors[Math.floor(Math.random() * colors.length)];
    particle.style.left = `${Math.random() * 100}%`;
    particle.style.top = `-20px`;
    
    const size = Math.floor(Math.random() * 6) + 6;
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    
    // Animation offsets
    particle.style.animationDelay = `${Math.random() * 2}s`;
    particle.style.animationDuration = `${Math.random() * 1.5 + 1.5}s`;
    
    overlay.appendChild(particle);

    // Auto-remove after cycle completes
    setTimeout(() => particle.remove(), 3500);
  }
}
