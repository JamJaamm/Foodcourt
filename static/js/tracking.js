/* ============================================================
   Choply — Order Tracking Page JS (tracking.js)
   Complete order tracking with 10-step timeline, rider info,
   OTP, notifications, support actions, and delivery completion.
   ============================================================ */
'use strict';

/* ══════════════════════════════════════════════
   STATUS CONSTANTS
   ══════════════════════════════════════════════ */
const TRACK = {
  TIMELINE_STEPS: [
    { key: 'order_placed',      label: 'Order Placed',              icon: 'fa-solid fa-receipt',        note: 'Your order has been placed successfully.' },
    { key: 'confirmed',         label: 'Order Confirmed',           icon: 'fa-solid fa-circle-check',   note: 'The restaurant has accepted your order.' },
    { key: 'preparing',         label: 'Preparing Order',           icon: 'fa-solid fa-fire-burner',    note: 'The kitchen is preparing your food.' },
    { key: 'ready',             label: 'Ready for Pickup',          icon: 'fa-solid fa-bag-shopping',   note: 'Your order is packed and ready for the rider.' },
    { key: 'rider_assigned',    label: 'Rider Assigned',            icon: 'fa-solid fa-user-check',     note: 'A rider has accepted your delivery.' },
    { key: 'rider_at_restaurant', label: 'Rider Arrived at Restaurant', icon: 'fa-solid fa-store',      note: 'Your rider has arrived at the restaurant.' },
    { key: 'picked_up',         label: 'Order Picked Up',           icon: 'fa-solid fa-box',            note: 'Your rider has picked up your order.' },
    { key: 'on_the_way',        label: 'On The Way',                icon: 'fa-solid fa-motorcycle',     note: 'Your rider is on the way to you.' },
    { key: 'rider_arrived',     label: 'Rider Arrived',             icon: 'fa-solid fa-location-dot',   note: 'Your rider has arrived at your location.' },
    { key: 'delivered',         label: 'Delivered',                  icon: 'fa-solid fa-party-horn',     note: 'Your order has been delivered successfully!' },
  ],

  STATUS_MESSAGES: {
    pending:          { msg: 'Your order is pending confirmation.',                    sub: 'The restaurant will review your order shortly.', icon: 'fa-solid fa-clock',              variant: '' },
    confirmed:        { msg: 'Your order has been confirmed!',                        sub: 'The restaurant is reviewing your order.',        icon: 'fa-solid fa-circle-check',       variant: '' },
    preparing:        { msg: 'The restaurant is preparing your food.',                sub: 'Your meal is being freshly prepared.',          icon: 'fa-solid fa-fire-burner',        variant: 'status-warning' },
    ready:            { msg: 'Your order is ready for pickup!',                       sub: 'Waiting for a rider to accept your delivery.',  icon: 'fa-solid fa-bag-shopping',       variant: 'status-success' },
    out_for_delivery: { msg: 'A rider has accepted your delivery.',                   sub: 'Your rider is heading to the restaurant.',      icon: 'fa-solid fa-motorcycle',         variant: '' },
    delivered:        { msg: 'Your order has been delivered successfully!',            sub: 'Enjoy your delicious meal!',                    icon: 'fa-solid fa-circle-check',       variant: 'status-delivered' },
    cancelled:        { msg: 'Your order has been cancelled.',                        sub: 'If you need help, contact our support team.',   icon: 'fa-solid fa-circle-xmark',       variant: '' },
  },

  DELIVERY_MESSAGES: {
    searching:            { msg: 'Searching for an available rider...',               sub: 'We\'re matching you with the best rider nearby.', icon: 'fa-solid fa-magnifying-glass',  variant: 'status-warning' },
    assigned:             { msg: 'A rider has accepted your delivery.',               sub: 'Your rider is heading to the restaurant.',        icon: 'fa-solid fa-user-check',        variant: '' },
    arrived_at_restaurant:{ msg: 'Your rider has arrived at the restaurant.',         sub: 'They\'re picking up your order now.',             icon: 'fa-solid fa-store',             variant: 'status-success' },
    picked_up:            { msg: 'Your rider has picked up your order.',              sub: 'Your food is on its way to you!',                icon: 'fa-solid fa-box',               variant: '' },
    on_the_way:           { msg: 'Your rider is on the way!',                        sub: 'Almost there — get ready to enjoy your meal.',   icon: 'fa-solid fa-motorcycle',        variant: '' },
    arrived:              { msg: 'Your rider has arrived!',                           sub: 'Meet your rider at the delivery location.',      icon: 'fa-solid fa-location-dot',      variant: 'status-success' },
    delivered:            { msg: 'Your order has been delivered successfully!',        sub: 'Thank you for ordering with Choply!',         icon: 'fa-solid fa-circle-check',      variant: 'status-delivered' },
    cancelled:            { msg: 'Your delivery has been cancelled.',                 sub: 'Contact support if you need assistance.',        icon: 'fa-solid fa-circle-xmark',      variant: '' },
  },

  NOTIFICATION_TEMPLATES: {
    confirmed:          { title: 'Order Confirmed',           msg: 'Your order has been confirmed by the restaurant.',     icon: 'fa-solid fa-circle-check', type: 'success' },
    preparing:          { title: 'Preparing Your Order',      msg: 'The restaurant is now preparing your delicious meal.', icon: 'fa-solid fa-fire-burner',  type: 'info' },
    ready:              { title: 'Ready for Pickup',          msg: 'Your order is packed and ready for rider pickup.',     icon: 'fa-solid fa-bag-shopping', type: 'info' },
    rider_assigned:     { title: 'Rider Assigned',            msg: 'A rider has accepted your delivery.',                  icon: 'fa-solid fa-user-check',   type: 'info' },
    rider_at_restaurant:{ title: 'Rider at Restaurant',       msg: 'Your rider has arrived at the restaurant.',            icon: 'fa-solid fa-store',        type: 'info' },
    picked_up:          { title: 'Order Picked Up',           msg: 'Your rider has picked up your order.',                 icon: 'fa-solid fa-box',          type: 'info' },
    on_the_way:         { title: 'On The Way',                msg: 'Your rider is heading to your location.',              icon: 'fa-solid fa-motorcycle',   type: 'info' },
    rider_arrived:      { title: 'Rider Arrived',             msg: 'Your rider is at the delivery location.',              icon: 'fa-solid fa-location-dot', type: 'warning' },
    delivered:          { title: 'Delivered!',                 msg: 'Your order has been delivered successfully.',          icon: 'fa-solid fa-party-horn',   type: 'success' },
  },

  /* Map delivery statuses to the 10-step timeline keys */
  DELIVERY_TO_TIMELINE: {
    'searching':             ['order_placed', 'confirmed', 'preparing', 'ready'],
    'assigned':              ['order_placed', 'confirmed', 'preparing', 'ready', 'rider_assigned'],
    'arrived_at_restaurant': ['order_placed', 'confirmed', 'preparing', 'ready', 'rider_assigned', 'rider_at_restaurant'],
    'picked_up':             ['order_placed', 'confirmed', 'preparing', 'ready', 'rider_assigned', 'rider_at_restaurant', 'picked_up'],
    'on_the_way':            ['order_placed', 'confirmed', 'preparing', 'ready', 'rider_assigned', 'rider_at_restaurant', 'picked_up', 'on_the_way'],
    'arrived':               ['order_placed', 'confirmed', 'preparing', 'ready', 'rider_assigned', 'rider_at_restaurant', 'picked_up', 'on_the_way', 'rider_arrived'],
    'delivered':             ['order_placed', 'confirmed', 'preparing', 'ready', 'rider_assigned', 'rider_at_restaurant', 'picked_up', 'on_the_way', 'rider_arrived', 'delivered'],
    'cancelled':             ['order_placed', 'confirmed'],
  },

  /* Map order statuses to the 4-step progress */
  ORDER_TO_PROGRESS: {
    pending: 1, confirmed: 1, preparing: 2, ready: 2,
    out_for_delivery: 3, delivered: 4, cancelled: 1,
  },

  DELIVERY_TO_PROGRESS: {
    searching: 2, assigned: 3, arrived_at_restaurant: 3,
    picked_up: 3, on_the_way: 3, arrived: 3, delivered: 4, cancelled: 1,
  },
};

/* ══════════════════════════════════════════════
   GLOBAL STATE
   ══════════════════════════════════════════════ */
let countdownSeconds = 0;
let countdownInterval = null;
let pollTimer = null;
let previousTimelineKey = '';
let orderData = null;

/* ══════════════════════════════════════════════
   INIT
   ══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  loadTrackingDetails();
  initRateStars();

  const modal = document.getElementById('past-order-modal');
  if (modal) {
    if (modal.parentElement && modal.parentElement !== document.body) {
      document.body.appendChild(modal);
    }
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closePastOrderModal();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePastOrderModal();
  });
});

/* ══════════════════════════════════════════════
   LOAD TRACKING DETAILS
   ══════════════════════════════════════════════ */
function loadTrackingDetails() {
  if (window.FOODCOURT_ORDER_DATA) {
    orderData = window.FOODCOURT_ORDER_DATA;
    renderAll(orderData);
    const isFinal = ['delivered', 'cancelled'].includes(orderData.status);
    if (!isFinal) startPolling(orderData.id);
    return;
  }

  /* No order data → show search / empty state */
  const activeId = localStorage.getItem('foodcourt_active_order_id');
  if (activeId) {
    fetchOrderById(activeId);
  } else {
    showEmptyState();
  }
}

function fetchOrderById(orderId) {
  fetch(`/api/delivery/${orderId}/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(r => r.json())
    .then(d => {
      if (d.error) { showEmptyState(); return; }
      orderData = d;
      renderAll(orderData);
      const isFinal = ['delivered', 'cancelled'].includes(orderData.status);
      if (!isFinal) startPolling(orderId);
    })
    .catch(() => showEmptyState());
}

function showEmptyState() {
  document.getElementById('track-status-banner').style.display = 'none';
  document.getElementById('track-progress-card').style.display = 'none';
  document.getElementById('track-empty-state').style.display = 'block';
}

/* ══════════════════════════════════════════════
   PAST ORDER DETAILS MODAL
   ══════════════════════════════════════════════ */
window.openPastOrderModal = function (orderId) {
  const modal = document.getElementById('past-order-modal');
  const content = document.getElementById('past-order-modal-content');
  if (!modal || !content) return;

  content.innerHTML = '<div class="track-modal-loading"><i class="fa-solid fa-spinner fa-spin"></i> Loading order details...</div>';
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';

  fetch(`/api/delivery/${orderId}/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(r => r.json())
    .then(d => {
      if (d.error) {
        content.innerHTML = '<div class="track-modal-loading"><i class="fa-solid fa-circle-xmark"></i> Order not found.</div>';
        return;
      }
      content.innerHTML = buildPastOrderModalHtml(d);
    })
    .catch(() => {
      content.innerHTML = '<div class="track-modal-loading"><i class="fa-solid fa-triangle-exclamation"></i> Failed to load order details.</div>';
    });
};

window.closePastOrderModal = function () {
  const modal = document.getElementById('past-order-modal');
  if (modal) modal.style.display = 'none';
  document.body.style.overflow = '';
};

function buildPastOrderModalHtml(d) {
  const badge = `<span class="track-status-badge ${getStatusBadgeClass(d.status)}">${capitalizeFirst(d.status.replace(/_/g, ' '))}</span>`;

  const dateStr = d.date
    ? new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '--';
  const payment = d.payment ? d.payment.charAt(0).toUpperCase() + d.payment.slice(1) : '--';

  const items = (d.items || []).map(item => {
    const img = item.image
      ? `<img src="${item.image}" alt="${escapeHtml(item.name)}" class="track-item-img">`
      : `<div class="track-item-img" style="display:flex;align-items:center;justify-content:center;font-size:20px;background:var(--bg-elevated);">🍽️</div>`;
    return `
      <div class="track-item-row">
        ${img}
        <div class="track-item-info">
          <div class="track-item-name">${escapeHtml(item.name)}</div>
          <div class="track-item-qty">Qty: ${item.qty}</div>
        </div>
        <div class="track-item-price">${formatPrice(item.price * item.qty)}</div>
      </div>`;
  }).join('') || '<div class="track-modal-empty">No items found.</div>';

  const discountRow = d.discount > 0
    ? `<div class="track-price-row"><span>Discount</span><span class="discount-value">-${formatPrice(d.discount)}</span></div>`
    : '';

  return `
    <div class="track-modal-head">
      <div>
        <div class="track-modal-label">Past Order</div>
        <div class="track-modal-id" id="past-order-modal-title">Order #${escapeHtml(d.id)}</div>
      </div>
      ${badge}
    </div>
    <div class="track-modal-restaurant">${escapeHtml(d.restaurant || '--')}</div>
    <div class="track-modal-meta">
      <span><i class="fa-regular fa-calendar"></i> ${dateStr}</span>
      <span><i class="fa-solid fa-credit-card"></i> ${escapeHtml(payment)}</span>
    </div>

    <div class="track-modal-section">
      <h4 class="track-modal-section-title"><i class="fa-solid fa-bag-shopping text-primary"></i> Order Items</h4>
      <div class="track-modal-items">${items}</div>
      <div class="track-modal-prices">
        <div class="track-price-row"><span>Subtotal</span><span>${formatPrice(d.subtotal)}</span></div>
        <div class="track-price-row"><span>Delivery Fee</span><span>${formatPrice(d.delivery_fee)}</span></div>
        ${discountRow}
        <div class="track-price-row grand-total"><span>Total</span><span>${formatPrice(d.total)}</span></div>
      </div>
      <div class="track-address-row">
        <i class="fa-solid fa-location-dot"></i>
        <div>
          <div class="track-modal-addr-label">Delivery Address</div>
          <div class="track-address-text">${escapeHtml(d.address || '--')}</div>
        </div>
      </div>
    </div>

    <div class="track-modal-section">
      <h4 class="track-modal-section-title"><i class="fa-solid fa-clock-rotate-left text-primary"></i> Delivery Timeline</h4>
      <div class="track-timeline">${buildTimelineHtml(d)}</div>
    </div>`;
}

/* ══════════════════════════════════════════════
   RENDER ALL
   ══════════════════════════════════════════════ */
function renderAll(data) {
  renderOrderHeader(data);
  renderStatusBanner(data);
  renderProgress(data);
  renderTimeline(data);
  renderRider(data);
  renderOtp(data);
  renderItems(data);
  renderPriceBreakdown(data);
  renderNotifications(data);
  renderSupportActions(data);
  renderCompletion(data);
  renderRateRider(data);
  renderCountdown(data);
  renderMapDriver(data);
}

/* ══════════════════════════════════════════════
   ORDER HEADER
   ══════════════════════════════════════════════ */
function renderOrderHeader(data) {
  setText('track-order-id', `Order #${data.id}`);
  setText('track-restaurant', data.restaurant || '--');
  setText('track-total', formatPrice(data.total));
  setText('track-payment', data.payment || '--');
  setText('track-address', data.address || '--');

  if (data.date) {
    const d = new Date(data.date);
    setText('track-date', d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }));
  }

  /* Status badge */
  const wrap = document.getElementById('track-status-badge-wrap');
  if (wrap) {
    const status = data.status;
    const badgeClass = getStatusBadgeClass(status);
    const needsPayment = status === 'pending'
      && data.payment_status
      && data.payment_status !== 'successful'
      && data.payment_status !== 'refunded';
    const payBtn = needsPayment
      ? `<a class="btn btn-primary btn-sm ms-2" href="/payments/retry/${encodeURIComponent(data.id)}/" style="text-decoration:none;vertical-align:middle;">
           <i class="fa-solid fa-credit-card me-1"></i> Pay Now
         </a>`
      : '';
    wrap.innerHTML = `<span class="track-status-badge ${badgeClass}">${capitalizeFirst(status.replace(/_/g, ' '))}</span>${payBtn}`;
  }

  /* ETA time */
  if (data.status !== 'delivered' && data.status !== 'cancelled') {
    const eta = new Date();
    eta.setMinutes(eta.getMinutes() + (data.delivery && data.delivery.status === 'on_the_way' ? 8 : 20));
    setText('track-eta-time', formatTime(eta));
  } else if (data.status === 'delivered') {
    setText('track-eta-time', 'Delivered');
  } else {
    setText('track-eta-time', '--:--');
  }
}

function getStatusBadgeClass(status) {
  const map = {
    pending: 'badge-pending', confirmed: 'badge-confirmed',
    preparing: 'badge-preparing', ready: 'badge-ready',
    out_for_delivery: 'badge-delivery', delivered: 'badge-delivered',
    cancelled: 'badge-cancelled',
  };
  return map[status] || 'badge-pending';
}

/* ══════════════════════════════════════════════
   STATUS BANNER
   ══════════════════════════════════════════════ */
function renderStatusBanner(data) {
  const banner = document.getElementById('track-status-banner');
  const iconEl = document.getElementById('track-status-icon');
  const msgEl = document.getElementById('track-status-msg');
  const subEl = document.getElementById('track-status-sub');

  let info;
  const delivery = data.delivery;

  if (delivery && delivery.status) {
    info = TRACK.DELIVERY_MESSAGES[delivery.status];
  }
  if (!info && data.status) {
    info = TRACK.STATUS_MESSAGES[data.status];
  }
  if (!info) {
    info = { msg: 'Tracking your order...', sub: 'Please wait.', icon: 'fa-solid fa-clock', variant: '' };
  }

  banner.className = 'track-status-banner ' + (info.variant || '');
  iconEl.innerHTML = `<i class="${info.icon}"></i>`;
  msgEl.textContent = info.msg;
  subEl.textContent = info.sub;
}

/* ══════════════════════════════════════════════
   4-STEP PROGRESS
   ══════════════════════════════════════════════ */
function renderProgress(data) {
  let step = 1;
  const delivery = data.delivery;

  if (delivery && delivery.status) {
    step = TRACK.DELIVERY_TO_PROGRESS[delivery.status] || 1;
  } else if (data.status) {
    step = TRACK.ORDER_TO_PROGRESS[data.status] || 1;
  }

  setTimeout(() => {
    const fillBar = document.getElementById('track-progress-fill');
    if (fillBar) fillBar.style.width = ((step - 1) / 3 * 100) + '%';

    for (let i = 1; i <= 4; i++) {
      const node = document.getElementById('step-node-' + i);
      if (!node) continue;
      if (i < step) {
        node.className = 'progress-step-node complete';
        node.querySelector('.progress-step-circle').innerHTML = '<i class="fa-solid fa-check"></i>';
      } else if (i === step) {
        node.className = 'progress-step-node active';
      } else {
        node.className = 'progress-step-node';
      }
    }
  }, 300);
}

/* ══════════════════════════════════════════════
   10-STEP VERTICAL TIMELINE
   ══════════════════════════════════════════════ */
function renderTimeline(data) {
  const container = document.getElementById('track-timeline');
  if (!container) return;
  container.innerHTML = buildTimelineHtml(data);
}

function buildTimelineHtml(data) {
  const delivery = data.delivery;
  const orderStatus = data.status;
  let completedKeys = [];

  if (delivery && delivery.status) {
    completedKeys = TRACK.DELIVERY_TO_TIMELINE[delivery.status] || [];
  } else {
    /* Map order status to timeline keys */
    const orderMap = {
      pending: [],
      confirmed: ['order_placed', 'confirmed'],
      preparing: ['order_placed', 'confirmed', 'preparing'],
      ready: ['order_placed', 'confirmed', 'preparing', 'ready'],
      out_for_delivery: ['order_placed', 'confirmed', 'preparing', 'ready'],
      delivered: ['order_placed', 'confirmed', 'preparing', 'ready', 'delivered'],
      cancelled: ['order_placed', 'confirmed'],
    };
    completedKeys = orderMap[orderStatus] || ['order_placed'];
  }

  const isCancelled = orderStatus === 'cancelled';
  const isDelivered = orderStatus === 'delivered';
  const activeKey = isDelivered ? 'delivered' : (completedKeys.length > 0 ? completedKeys[completedKeys.length - 1] : 'order_placed');

  /* Build log timestamps from delivery logs */
  const logTimestamps = {};
  if (delivery && delivery.logs) {
    delivery.logs.forEach(log => {
      const key = logKeyFromLabel(log.label);
      if (key) logTimestamps[key] = log.created_at;
    });
  }

  return TRACK.TIMELINE_STEPS.map(step => {
    const isCompleted = completedKeys.includes(step.key);
    const isActive = step.key === activeKey && !isDelivered && !isCancelled;
    const isFuture = !isCompleted && !isActive;

    let cls = 'track-timeline-item';
    if (isCompleted && !isActive) cls += ' completed';
    else if (isActive) cls += ' active';
    else cls += ' disabled';

    const icon = isCompleted && !isActive
      ? '<i class="fa-solid fa-check" style="font-size:8px;color:#fff;"></i>'
      : `<i class="${step.icon}" style="font-size:8px;${isActive ? 'color:var(--primary)' : 'color:var(--text-muted)'}"></i>`;

    const time = logTimestamps[step.key]
      ? `<div class="track-timeline-time">${formatClock(logTimestamps[step.key])}</div>`
      : '';

    return `
      <div class="${cls}">
        <div class="track-timeline-dot">${icon}</div>
        <div class="track-timeline-title">${step.label}</div>
        <div class="track-timeline-note">${step.note}</div>
        ${time}
      </div>`;
  }).join('');
}

function logKeyFromLabel(label) {
  const l = (label || '').toLowerCase();
  if (l.includes('placed')) return 'order_placed';
  if (l.includes('confirmed')) return 'confirmed';
  if (l.includes('prepar')) return 'preparing';
  if (l.includes('ready')) return 'ready';
  if (l.includes('rider assigned') || l.includes('assigned')) return 'rider_assigned';
  if (l.includes('arrived at') || l.includes('at restaurant')) return 'rider_at_restaurant';
  if (l.includes('picked up') || l.includes('pickup')) return 'picked_up';
  if (l.includes('on the way') || l.includes('heading')) return 'on_the_way';
  if (l.includes('arrived') || l.includes('at your')) return 'rider_arrived';
  if (l.includes('delivered')) return 'delivered';
  return null;
}

/* ══════════════════════════════════════════════
   RIDER INFO
   ══════════════════════════════════════════════ */
function renderRider(data) {
  const delivery = data.delivery;
  const rider = delivery && delivery.rider;
  const searching = document.getElementById('track-rider-searching');
  const details = document.getElementById('track-rider-details');

  if (rider) {
    searching.style.display = 'none';
    details.style.display = 'block';

    const avatar = document.getElementById('driver-avatar');
    const name = document.getElementById('driver-name');
    const vehicle = document.getElementById('driver-vehicle');
    const rating = document.getElementById('driver-rating');
    const trips = document.getElementById('driver-trips');
    const call = document.getElementById('driver-call');

    if (name) name.textContent = rider.name || '--';
    if (vehicle) vehicle.textContent = [rider.vehicle, rider.vehicle_plate].filter(Boolean).join(' · ') || '--';
    if (rating) rating.textContent = rider.rating || '0';
    if (trips) trips.textContent = rider.trips || '0';
    if (avatar) avatar.src = rider.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&q=80';
    if (call) call.href = `tel:${rider.phone || ''}`;
  } else {
    /* Show searching state only if we're before delivered */
    const showSearching = data.status !== 'delivered' && data.status !== 'cancelled';
    searching.style.display = showSearching ? 'flex' : 'none';
    details.style.display = 'none';
  }
}

/* ══════════════════════════════════════════════
   OTP
   ══════════════════════════════════════════════ */
function renderOtp(data) {
  const card = document.getElementById('otp-card');
  const otpEl = document.getElementById('delivery-otp');
  if (!card || !otpEl) return;

  const delivery = data.delivery;
  const showOtp = delivery
    && ['picked_up', 'on_the_way', 'arrived'].includes(delivery.status)
    && delivery.otp;

  card.style.display = showOtp ? 'block' : 'none';
  if (showOtp) otpEl.textContent = delivery.otp;
}

/* ══════════════════════════════════════════════
   ORDER ITEMS
   ══════════════════════════════════════════════ */
function renderItems(data) {
  const container = document.getElementById('track-order-items');
  if (!container) return;

  const items = data.items || [];
  if (!items.length) {
    container.innerHTML = '<div style="font-size:13px;color:var(--text-muted);padding:12px 0;">No items found.</div>';
    return;
  }

  container.innerHTML = items.map(item => {
    const img = item.image
      ? `<img src="${item.image}" alt="${item.name}" class="track-item-img">`
      : `<div class="track-item-img" style="display:flex;align-items:center;justify-content:center;font-size:20px;background:var(--bg-elevated);">🍽️</div>`;

    const instruction = item.instruction
      ? `<div class="track-item-instruction"><i class="fa-solid fa-circle-info"></i> ${escapeHtml(item.instruction)}</div>`
      : '';

    return `
      <div class="track-item-row">
        ${img}
        <div class="track-item-info">
          <div class="track-item-name">${escapeHtml(item.name)}</div>
          <div class="track-item-qty">Qty: ${item.qty}</div>
          ${instruction}
        </div>
        <div class="track-item-price">${formatPrice(item.price * item.qty)}</div>
      </div>`;
  }).join('');
}

/* ══════════════════════════════════════════════
   PRICE BREAKDOWN
   ══════════════════════════════════════════════ */
function renderPriceBreakdown(data) {
  setText('track-subtotal', formatPrice(data.subtotal || 0));
  setText('track-delivery-fee', formatPrice(data.delivery_fee || 0));
  setText('track-grand-total', formatPrice(data.total || 0));

  const discountRow = document.getElementById('track-discount-row');
  if (data.discount && data.discount > 0) {
    discountRow.style.display = 'flex';
    setText('track-discount', '-' + formatPrice(data.discount));
  } else {
    discountRow.style.display = 'none';
  }
}

/* ══════════════════════════════════════════════
   NOTIFICATIONS
   ══════════════════════════════════════════════ */
function renderNotifications(data) {
  const container = document.getElementById('track-notifications');
  if (!container) return;

  const notifications = [];
  const delivery = data.delivery;
  const orderStatus = data.status;

  /* Determine which notifications to show */
  if (orderStatus === 'cancelled') {
    notifications.push({ ...TRACK.NOTIFICATION_TEMPLATES.confirmed, time: data.date });
    notifications.push({ title: 'Order Cancelled', msg: 'Your order has been cancelled.', icon: 'fa-solid fa-circle-xmark', type: 'error', time: new Date().toISOString() });
  } else {
    const stepsToShow = ['confirmed'];
    if (delivery && delivery.status) {
      const mapping = {
        preparing: ['preparing'], ready: ['ready'],
        assigned: ['rider_assigned'], arrived_at_restaurant: ['rider_at_restaurant'],
        picked_up: ['picked_up'], on_the_way: ['on_the_way'],
        arrived: ['rider_arrived'], delivered: ['delivered'],
      };
      const addSteps = mapping[delivery.status] || [];
      stepsToShow.push(...addSteps);
    } else if (orderStatus) {
      const mapping = { preparing: ['preparing'], ready: ['ready'] };
      const addSteps = mapping[orderStatus] || [];
      stepsToShow.push(...addSteps);
    }

    stepsToShow.forEach(stepKey => {
      const tmpl = TRACK.NOTIFICATION_TEMPLATES[stepKey];
      if (tmpl) {
        /* Try to find a timestamp from logs */
        let time = data.date;
        if (delivery && delivery.logs) {
          const matchingLog = delivery.logs.find(l => logKeyFromLabel(l.label) === stepKey);
          if (matchingLog) time = matchingLog.created_at;
        }
        notifications.push({ ...tmpl, time });
      }
    });
  }

  if (!notifications.length) {
    container.innerHTML = '<div style="font-size:13px;color:var(--text-muted);padding:8px 0;">No notifications yet.</div>';
    return;
  }

  container.innerHTML = notifications.map((n, i) => `
    <div class="track-notify-card" style="animation-delay:${i * 60}ms;">
      <div class="notify-icon ${n.type || 'info'}"><i class="${n.icon}"></i></div>
      <div class="notify-body">
        <div class="notify-title">${n.title}</div>
        <div class="notify-msg">${n.msg}</div>
        <div class="notify-time">${n.time ? timeAgo(n.time) : ''}</div>
      </div>
    </div>`).join('');
}

/* ══════════════════════════════════════════════
   SUPPORT ACTIONS
   ══════════════════════════════════════════════ */
function renderSupportActions(data) {
  const delivery = data.delivery;
  const status = data.status;
  const hasRider = delivery && delivery.rider;

  /* Call Rider - only show when rider assigned and order not delivered/cancelled */
  toggleEl('btn-call-rider', hasRider && !['delivered', 'cancelled'].includes(status));

  /* Contact Restaurant - show unless delivered/cancelled */
  toggleEl('btn-contact-restaurant', !['delivered', 'cancelled'].includes(status));

  /* Report Issue - always show */
  toggleEl('btn-report-issue', true);

  /* Cancel Order - only if not prepared/delivered/cancelled */
  const canCancel = ['pending', 'confirmed'].includes(status);
  toggleEl('btn-cancel-order', canCancel);
}

/* ══════════════════════════════════════════════
   DELIVERY COMPLETION
   ══════════════════════════════════════════════ */
function renderCompletion(data) {
  const completionEl = document.getElementById('track-completion');
  if (!completionEl) return;

  if (data.status === 'delivered') {
    completionEl.style.display = 'block';
    spawnConfetti();
  } else {
    completionEl.style.display = 'none';
  }
}

function spawnConfetti() {
  const colors = ['#FF6B35', '#06D6A0', '#FFB800', '#FF4757', '#3B82F6', '#2ED573'];
  for (let i = 0; i < 40; i++) {
    const el = document.createElement('div');
    el.className = 'track-confetti';
    el.style.left = Math.random() * 100 + 'vw';
    el.style.background = colors[Math.floor(Math.random() * colors.length)];
    el.style.animationDelay = Math.random() * 2 + 's';
    el.style.animationDuration = (2 + Math.random() * 2) + 's';
    el.style.width = (6 + Math.random() * 8) + 'px';
    el.style.height = (6 + Math.random() * 8) + 'px';
    el.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 5000);
  }
}

/* ══════════════════════════════════════════════
   RATE RIDER
   ══════════════════════════════════════════════ */
function renderRateRider(data) {
  const card = document.getElementById('rate-rider-card');
  if (!card) return;

  if (data.can_rate && data.delivery && data.delivery.rider) {
    card.style.display = 'block';
    setText('rate-rider-name', data.delivery.rider.name || 'your rider');
  } else {
    card.style.display = 'none';
  }
}

function initRateStars() {
  const container = document.getElementById('rate-stars');
  if (!container) return;

  container.querySelectorAll('[data-star]').forEach(star => {
    star.addEventListener('click', () => {
      const value = parseInt(star.dataset.star, 10);
      document.getElementById('rider-rating-value').value = value;
      container.querySelectorAll('[data-star]').forEach(s => {
        const n = parseInt(s.dataset.star, 10);
        s.className = n <= value ? 'fa-solid fa-star active' : 'fa-regular fa-star';
      });
    });

    star.addEventListener('mouseenter', () => {
      const value = parseInt(star.dataset.star, 10);
      container.querySelectorAll('[data-star]').forEach(s => {
        const n = parseInt(s.dataset.star, 10);
        if (n <= value) s.style.color = 'var(--warning)';
      });
    });

    star.addEventListener('mouseleave', () => {
      const current = parseInt(document.getElementById('rider-rating-value').value, 10);
      container.querySelectorAll('[data-star]').forEach(s => {
        const n = parseInt(s.dataset.star, 10);
        s.style.color = n <= current ? 'var(--warning)' : '#d1d5db';
      });
    });
  });
}

window.submitRiderReview = function () {
  const orderId = orderData ? orderData.id : null;
  const rating = parseInt(document.getElementById('rider-rating-value').value, 10) || 0;
  const comment = document.getElementById('rider-review-comment').value;

  if (!rating) {
    if (window.Toast) Toast.show('Please select a star rating', 'error');
    return;
  }

  const form = new FormData();
  form.append('rating', rating);
  form.append('comment', comment);

  fetch(`/api/orders/${orderId}/rate-rider/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
    body: form,
  }).then(r => r.json()).then(d => {
    if (d.success) {
      if (window.Toast) Toast.show('Review submitted! Thanks for the feedback.', 'success');
      document.getElementById('rate-rider-card').style.display = 'none';
    } else {
      if (window.Toast) Toast.show(d.error || 'Failed to submit review', 'error');
    }
  }).catch(() => {
    if (window.Toast) Toast.show('Failed to submit review', 'error');
  });
};

/* ══════════════════════════════════════════════
   COUNTDOWN & ETA
   ══════════════════════════════════════════════ */
function renderCountdown(data) {
  const timerEl = document.getElementById('countdown-timer');
  const subtextEl = document.getElementById('countdown-subtext');
  const progressWrap = document.getElementById('track-eta-progress');
  const progressFill = document.getElementById('track-eta-bar-fill');

  if (!timerEl) return;

  if (data.status === 'delivered') {
    timerEl.textContent = '00:00';
    if (subtextEl) subtextEl.innerHTML = '<span style="color:var(--success);font-weight:700;">Delivered! Enjoy your meal!</span>';
    if (progressWrap) progressWrap.style.display = 'block';
    if (progressFill) progressFill.style.width = '100%';
    if (countdownInterval) clearInterval(countdownInterval);
    return;
  }

  if (data.status === 'cancelled') {
    timerEl.textContent = '--:--';
    if (subtextEl) subtextEl.textContent = 'Order has been cancelled.';
    if (progressWrap) progressWrap.style.display = 'none';
    if (countdownInterval) clearInterval(countdownInterval);
    return;
  }

  /* Calculate ETA based on delivery status */
  const delivery = data.delivery;
  let minutes = 20;
  if (delivery) {
    const etaMap = {
      searching: 25, assigned: 18, arrived_at_restaurant: 14,
      picked_up: 10, on_the_way: 6, arrived: 1,
    };
    minutes = etaMap[delivery.status] || 20;
  } else if (data.status === 'preparing' || data.status === 'ready') {
    minutes = 22;
  }

  countdownSeconds = minutes * 60;

  if (countdownInterval) clearInterval(countdownInterval);
  countdownInterval = setInterval(() => {
    countdownSeconds--;
    if (countdownSeconds <= 0) {
      countdownSeconds = 0;
      clearInterval(countdownInterval);
    }
    const mins = String(Math.floor(countdownSeconds / 60)).padStart(2, '0');
    const secs = String(countdownSeconds % 60).padStart(2, '0');
    timerEl.textContent = `${mins}:${secs}`;
  }, 1000);

  /* Subtext */
  const subtextMap = {
    searching: 'Waiting for a rider to accept your order.',
    assigned: 'Your rider is heading to the restaurant.',
    arrived_at_restaurant: 'Your rider is picking up your order.',
    picked_up: 'Your food is on its way to you!',
    on_the_way: 'Almost there — get ready!',
    arrived: 'Meet your rider at the door.',
  };
  if (subtextEl) {
    subtextEl.textContent = (delivery && subtextMap[delivery.status]) || 'Your order is being prepared.';
  }

  /* Progress bar */
  if (progressWrap) {
    progressWrap.style.display = 'block';
    const progressMap = {
      searching: 15, assigned: 30, arrived_at_restaurant: 45,
      picked_up: 60, on_the_way: 80, arrived: 95, delivered: 100,
    };
    const pct = (delivery && progressMap[delivery.status]) || 10;
    if (progressFill) {
      setTimeout(() => { progressFill.style.width = pct + '%'; }, 400);
    }
  }
}

/* ══════════════════════════════════════════════
   MAP DRIVER
   ══════════════════════════════════════════════ */
function renderMapDriver(data) {
  const scooter = document.getElementById('driver-scooter');
  if (!scooter) return;

  const delivery = data.delivery;
  const showMap = delivery && ['assigned', 'arrived_at_restaurant', 'picked_up', 'on_the_way', 'arrived'].includes(delivery.status);

  scooter.style.display = showMap ? 'flex' : 'none';

  if (showMap) {
    animateRiderOnMap(delivery.status);
  }
}

function animateRiderOnMap(status) {
  const scooter = document.getElementById('driver-scooter');
  if (!scooter) return;

  scooter.style.transition = 'top 4s ease-in-out, left 4s ease-in-out';

  const posMap = {
    assigned:              { top: '15%', left: '15%' },
    arrived_at_restaurant: { top: '30%', left: '38%' },
    picked_up:             { top: '32%', left: '42%' },
    on_the_way:            { top: '55%', left: '65%' },
    arrived:               { top: '68%', left: '78%' },
  };

  const pos = posMap[status] || { top: '30%', left: '40%' };
  scooter.style.top = pos.top;
  scooter.style.left = pos.left;
}

/* ══════════════════════════════════════════════
   LIVE POLLING (WebSocket-ready structure)
   ══════════════════════════════════════════════ */
function startPolling(orderId) {
  if (!orderId) return;
  if (pollTimer) clearInterval(pollTimer);

  pollTimer = setInterval(() => {
    fetch(`/api/delivery/${orderId}/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.json())
      .then(d => {
        if (d.error) return;

        /* Update local data */
        orderData.status = d.status;
        orderData.delivery = d.delivery;
        orderData.can_rate = d.can_rate;

        renderAll(orderData);

        /* Show toast for new timeline entries */
        if (d.delivery && d.delivery.logs && d.delivery.logs.length > 0) {
          const newest = d.delivery.logs[0];
          const currentKey = logKeyFromLabel(newest.label);
          if (currentKey && currentKey !== previousTimelineKey && currentKey !== 'order_placed') {
            if (window.Toast) Toast.show(`${newest.label}!`, 'info');
          }
          previousTimelineKey = currentKey;
        }

        /* Stop polling on final status */
        if (['delivered', 'cancelled'].includes(d.status)) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      })
      .catch(() => {});
  }, 8000);

  /* Capture initial timeline key */
  if (orderData.delivery && orderData.delivery.logs && orderData.delivery.logs.length > 0) {
    previousTimelineKey = logKeyFromLabel(orderData.delivery.logs[0].label);
  }
}

/* ══════════════════════════════════════════════
   SUPPORT HANDLERS
   ══════════════════════════════════════════════ */
window.handleCallRider = function () {
  const delivery = orderData && orderData.delivery;
  if (delivery && delivery.rider && delivery.rider.phone) {
    window.location.href = `tel:${delivery.rider.phone}`;
  } else {
    if (window.Toast) Toast.show('No rider phone number available.', 'warning');
  }
};

window.handleContactRestaurant = function () {
  if (window.Toast) Toast.show('Restaurant contact feature coming soon!', 'info');
};

window.handleReportIssue = function () {
  if (window.Toast) Toast.show('Issue reported. Our team will review it shortly.', 'success');
};

window.handleCancelOrder = function () {
  if (!orderData) return;
  if (!confirm('Are you sure you want to cancel this order?')) return;

  fetch(`/api/orders/${orderData.id}/cancel/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
  }).then(r => r.json()).then(d => {
    if (d.success) {
      if (window.Toast) Toast.show('Order cancelled.', 'info');
      orderData.status = 'cancelled';
      renderAll(orderData);
    } else {
      if (window.Toast) Toast.show(d.error || 'Unable to cancel order.', 'error');
    }
  }).catch(() => {
    if (window.Toast) Toast.show('Failed to cancel order.', 'error');
  });
};

/* ══════════════════════════════════════════════
   DOWNLOAD RECEIPT
   ══════════════════════════════════════════════ */
window.downloadReceipt = function () {
  if (!orderData) return;

  let receipt = `Choply Receipt\n`;
  receipt += `${'═'.repeat(40)}\n`;
  receipt += `Order: #${orderData.id}\n`;
  receipt += `Restaurant: ${orderData.restaurant || '--'}\n`;
  receipt += `Date: ${orderData.date ? new Date(orderData.date).toLocaleString() : '--'}\n`;
  receipt += `Address: ${orderData.address || '--'}\n`;
  receipt += `${'─'.repeat(40)}\n`;

  (orderData.items || []).forEach(item => {
    receipt += `${item.qty}x ${item.name.padEnd(25)} ${formatPrice(item.price * item.qty).padStart(8)}\n`;
  });

  receipt += `${'─'.repeat(40)}\n`;
  receipt += `${'Subtotal'.padEnd(30)} ${formatPrice(orderData.subtotal || 0).padStart(8)}\n`;
  receipt += `${'Delivery Fee'.padEnd(30)} ${formatPrice(orderData.delivery_fee || 0).padStart(8)}\n`;
  if (orderData.discount > 0) receipt += `${'Discount'.padEnd(30)} -${formatPrice(orderData.discount).padStart(7)}\n`;
  receipt += `${'─'.repeat(40)}\n`;
  receipt += `${'TOTAL'.padEnd(30)} ${formatPrice(orderData.total || 0).padStart(8)}\n`;
  receipt += `${'═'.repeat(40)}\n`;
  receipt += `Payment: ${orderData.payment || '--'}\n`;
  receipt += `Thank you for ordering with Choply!\n`;

  const blob = new Blob([receipt], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Choply-Receipt-${orderData.id}.txt`;
  a.click();
  URL.revokeObjectURL(url);
};

/* ══════════════════════════════════════════════
   HELPERS
   ══════════════════════════════════════════════ */
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function toggleEl(id, show) {
  const el = document.getElementById(id);
  if (el) el.style.display = show ? '' : 'none';
}

function formatPrice(p) {
  return '₦' + Number(p || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatTime(d) {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function formatClock(iso) {
  const d = new Date(iso);
  return formatTime(d);
}

function capitalizeFirst(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

function timeAgo(iso) {
  const s = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return Math.floor(s / 60) + 'm ago';
  if (s < 86400) return Math.floor(s / 3600) + 'h ago';
  return new Date(iso).toLocaleDateString();
}

function getCookie(name) {
  let val = null;
  if (document.cookie && document.cookie !== '') {
    document.cookie.split(';').forEach(c => {
      c = c.trim();
      if (c.substring(0, name.length + 1) === (name + '=')) {
        val = decodeURIComponent(c.substring(name.length + 1));
      }
    });
  }
  return val;
}
