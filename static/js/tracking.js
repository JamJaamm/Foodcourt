/* ============================================================
   FoodCourt — Order Tracking Page JS (tracking.js)
   ============================================================ */
'use strict';

let countdownSeconds = 720; // 12 minutes in seconds
let countdownInterval = null;
let updateFeedTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
  loadTrackingDetails();
  initProgressTracker();
  initCountdownTimer();
  animateRiderOnMap();
  initUpdatesFeed();
});

/* ══════════════════════════════════════════════
   LOAD DETAILS (LOCALSTORAGE OR FALLBACK)
   ══════════════════════════════════════════════ */
function loadTrackingDetails() {
  const activeId = localStorage.getItem('foodcourt_active_order_id');
  const activeAddr = localStorage.getItem('foodcourt_active_order_address');
  const activeTotal = localStorage.getItem('foodcourt_active_order_total');

  let orderId = activeId || 'FC-2026-8472';
  let address = activeAddr || '12 Maple Street, Apt 4B, Downtown';
  let totalAmount = activeTotal || '$59.54';
  
  // Set in DOM
  document.getElementById('track-order-id').textContent = `Order ${orderId}`;
  document.getElementById('track-address-label').textContent = address;
  document.getElementById('track-amount-paid').textContent = totalAmount;

  // Render items - fallback to mock order items
  const itemsContainer = document.getElementById('order-tracking-items');
  if (itemsContainer && window.FOODCOURT_DATA) {
    const mockOrder = window.FOODCOURT_DATA.orders[0];
    itemsContainer.innerHTML = mockOrder.items.map(item => `
      <div class="d-flex justify-content-between align-items-center mb-2" style="font-size:13px;color:var(--text-secondary);">
        <span>${item.qty} × ${item.name}</span>
        <span>${window.formatPrice(item.price * item.qty)}</span>
      </div>
    `).join('');
  }

  // Set initial driver details from mock data
  if (window.FOODCOURT_DATA) {
    const driver = window.FOODCOURT_DATA.driver;
    document.getElementById('driver-avatar').src = driver.avatar;
    document.getElementById('driver-name').textContent = driver.name;
    document.getElementById('driver-vehicle').textContent = driver.vehicle;
    document.getElementById('driver-call').setAttribute('href', `tel:${driver.phone}`);
  }

  // Set dynamic ETA timestamp in header (now + 12 minutes)
  const etaTime = new Date();
  etaTime.setMinutes(etaTime.getMinutes() + 12);
  const hrs = String(etaTime.getHours()).padStart(2, '0');
  const mins = String(etaTime.getMinutes()).padStart(2, '0');
  document.getElementById('track-eta-time').textContent = `${hrs}:${mins}`;
}

/* ══════════════════════════════════════════════
   INIT PROGRESS BAR NODES
   ══════════════════════════════════════════════ */
function initProgressTracker() {
  const fillBar = document.getElementById('track-progress-fill');
  if (fillBar) {
    // Fill to 66% (Step 3: On the Way is active)
    setTimeout(() => {
      fillBar.style.width = '66%';
    }, 500);
  }
}

/* ══════════════════════════════════════════════
   ETA COUNTDOWN TIMER
   ══════════════════════════════════════════════ */
function initCountdownTimer() {
  const timerEl = document.getElementById('countdown-timer');
  const subtextEl = document.getElementById('countdown-subtext');
  if (!timerEl) return;

  countdownInterval = setInterval(() => {
    countdownSeconds--;
    
    if (countdownSeconds <= 0) {
      clearInterval(countdownInterval);
      // Trigger order completed delivered
      completeOrderDelivery();
      return;
    }

    const mins = String(Math.floor(countdownSeconds / 60)).padStart(2, '0');
    const secs = String(countdownSeconds % 60).padStart(2, '0');
    timerEl.textContent = `${mins}:${secs}`;
  }, 1000);
}

function completeOrderDelivery() {
  const timerEl = document.getElementById('countdown-timer');
  const subtextEl = document.getElementById('countdown-subtext');
  
  if (timerEl) timerEl.textContent = '00:00';
  if (subtextEl) {
    subtextEl.innerHTML = `<span class="text-success fw-bold">🎉 Delivered! Enjoy your delicious meal!</span>`;
  }

  // Animate progress to Step 4 (Delivered)
  const node3 = document.getElementById('step-node-3');
  const node4 = document.getElementById('step-node-4');
  const fillBar = document.getElementById('track-progress-fill');

  if (node3) {
    node3.classList.remove('active');
    node3.classList.add('complete');
    node3.querySelector('.progress-step-circle').innerHTML = `<i class="fa-solid fa-check"></i>`;
  }

  if (node4) {
    node4.classList.add('complete');
    node4.querySelector('.progress-step-circle').innerHTML = `<i class="fa-solid fa-check"></i>`;
  }

  if (fillBar) fillBar.style.width = '100%';

  // Prepend final notification on feed
  addTimelineLog('📦 Delivered', 'Your order has been delivered successfully. Enjoy your hot food!', new Date());
  
  // Show celebration toast
  Toast.show('Your order has been delivered! Enjoy! 🍔🍕', 'success');
}

/* ══════════════════════════════════════════════
   LIVE MAP RIDER SCRAMBLER ANIMATIONS
   ══════════════════════════════════════════════ */
function animateRiderOnMap() {
  const scooter = document.getElementById('driver-scooter');
  if (!scooter) return;

  // Restaurant pin is at Top 30%, Left 40%
  // Home pin is at Top 70%, Left 80%
  
  // Let's place it at Restaurant to start
  scooter.style.top = '30%';
  scooter.style.left = '40%';

  // Sequential coordinates routing along standard horizontal/vertical roads
  setTimeout(() => {
    // Stage 1: Drive to intersection: Top 30%, Left 80% (crossroad)
    scooter.style.top = '30%';
    scooter.style.left = '80%';
  }, 1000);

  setTimeout(() => {
    // Stage 2: Drive south along road 4: Top 55%, Left 80% (midway)
    scooter.style.top = '55%';
    scooter.style.left = '80%';
  }, 12000);

  setTimeout(() => {
    // Stage 3: Arrive at Home: Top 70%, Left 80%
    scooter.style.top = '70%';
    scooter.style.left = '80%';
  }, 24000);
}

/* ══════════════════════════════════════════════
   TIMELINE FEED UPDATE SIMULATOR
   ══════════════════════════════════════════════ */
function initUpdatesFeed() {
  const container = document.getElementById('tracking-timeline');
  if (!container) return;

  // Historical log entries
  const now = new Date();
  
  const timeConfirmed = new Date(now.getTime() - 12 * 60 * 1000);
  const timePrepared = new Date(now.getTime() - 8 * 60 * 1000);
  const timeTransit = new Date(now.getTime() - 2 * 60 * 1000);

  container.innerHTML = `
    <div class="timeline-item">
      <div class="timeline-dot"></div>
      <div class="timeline-title">🛵 On the Way</div>
      <div class="timeline-desc text-secondary" style="font-size:12px;margin-top:2px;">Our courier Marcus Johnson is on his way to your destination.</div>
      <div class="timeline-time">${formatTime(timeTransit)}</div>
    </div>
    <div class="timeline-item">
      <div class="timeline-dot"></div>
      <div class="timeline-title">🍳 Food Prepared</div>
      <div class="timeline-desc text-secondary" style="font-size:12px;margin-top:2px;">The chefs have packed your delicious meal. Piping hot and ready.</div>
      <div class="timeline-time">${formatTime(timePrepared)}</div>
    </div>
    <div class="timeline-item">
      <div class="timeline-dot"></div>
      <div class="timeline-title">✓ Order Confirmed</div>
      <div class="timeline-desc text-secondary" style="font-size:12px;margin-top:2px;">The Burger Lab received and accepted your order.</div>
      <div class="timeline-time">${formatTime(timeConfirmed)}</div>
    </div>
  `;

  // Make the top active log look active
  const topLog = container.querySelector('.timeline-item');
  if (topLog) topLog.classList.add('active');

  // Stage a new update 20s from now
  setTimeout(() => {
    addTimelineLog('📍 Nearby', 'Rider is nearby, arriving in approximately 2 minutes. Please be ready!', new Date());
  }, 20000);
}

function addTimelineLog(title, desc, timestamp) {
  const container = document.getElementById('tracking-timeline');
  if (!container) return;

  // Clear current active log state
  container.querySelectorAll('.timeline-item').forEach(el => el.classList.remove('active'));

  const item = document.createElement('div');
  item.className = 'timeline-item active reveal';
  item.innerHTML = `
    <div class="timeline-dot"></div>
    <div class="timeline-title">${title}</div>
    <div class="timeline-desc text-secondary" style="font-size:12px;margin-top:2px;">${desc}</div>
    <div class="timeline-time">${formatTime(timestamp)}</div>
  `;

  container.prepend(item);
  Toast.show(`Update: ${title}! 🛵`, 'info');

  if (window.ScrollReveal) {
    window.ScrollReveal.init();
  }
}

/* ── Helpers ── */
function formatTime(date) {
  const h = String(date.getHours()).padStart(2, '0');
  const m = String(date.getMinutes()).padStart(2, '0');
  return `${h}:${m}`;
}
