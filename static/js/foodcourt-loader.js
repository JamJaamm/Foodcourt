/* ============================================================
   Choply — Loading Animation System (JS)
   ============================================================ */
(function () {
  'use strict';

  /* ── Messages that rotate while loading ── */
  var MESSAGES = [
    'Preparing your order',
    'Adding the finishing touches',
    'Almost ready',
    'Your food is on its way'
  ];
  var MSG_INTERVAL = 2400;

  var overlay = null;
  var textEl = null;
  var msgTimer = null;
  var msgIndex = 0;
  var loaderActive = false;

  /* ──────────────────────────────────────
     INITIALISE — call once after DOM ready
     ────────────────────────────────────── */
  function init() {
    overlay = document.getElementById('fc-loader-overlay');
    textEl = document.getElementById('fc-loader-text');
    if (!overlay) return;

    /* Hide the loader once the page fully loads */
    window.addEventListener('load', function () {
      setTimeout(hideLoader, 300);
    });
  }

  /* ──────────────────────────────────────
     SHOW LOADER
     ────────────────────────────────────── */
  function showLoader(opts) {
    if (!overlay) init();
    if (!overlay) return;

    clearTimeout(msgTimer);
    msgIndex = 0;
    loaderActive = true;

    overlay.classList.remove('fc-loader-hide', 'fc-loader-hidden');
    document.body.style.overflow = 'hidden';

    if (textEl) textEl.textContent = MESSAGES[0];
    startMessageCycle();
  }

  /* ──────────────────────────────────────
     HIDE LOADER
     ────────────────────────────────────── */
  function hideLoader(callback) {
    if (!overlay) return;
    if (!loaderActive && overlay.classList.contains('fc-loader-hidden')) return;

    loaderActive = false;
    clearTimeout(msgTimer);

    overlay.classList.add('fc-loader-hide');
    document.body.style.overflow = '';

    setTimeout(function () {
      overlay.classList.add('fc-loader-hidden');
      if (typeof callback === 'function') callback();
    }, 420);
  }

  /* ──────────────────────────────────────
     MESSAGE CYCLING
     ────────────────────────────────────── */
  function startMessageCycle() {
    clearTimeout(msgTimer);
    msgTimer = setInterval(function () {
      if (!loaderActive) return;
      msgIndex = (msgIndex + 1) % MESSAGES.length;
      if (textEl) {
        textEl.style.opacity = '0';
        setTimeout(function () {
          textEl.textContent = MESSAGES[msgIndex];
          textEl.style.opacity = '1';
        }, 200);
      }
    }, MSG_INTERVAL);
  }

  /* ──────────────────────────────────────
     BUTTON LOADING STATES
     ────────────────────────────────────── */
  function setBtnLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
      if (!btn.dataset.origText) {
        btn.dataset.origText = btn.innerHTML;
      }
      btn.classList.add('fc-btn-loading');
      btn.disabled = true;
      btn.innerHTML =
        '<span class="fc-btn-text">' + (btn.dataset.origText || '') + '</span>' +
        '<span class="fc-btn-spinner">' +
          '<span class="fc-btn-spinner-dot"></span>' +
          '<span class="fc-btn-spinner-dot"></span>' +
          '<span class="fc-btn-spinner-dot"></span>' +
        '</span>';
    } else {
      btn.classList.remove('fc-btn-loading');
      btn.disabled = false;
      if (btn.dataset.origText) {
        btn.innerHTML = btn.dataset.origText;
        delete btn.dataset.origText;
      }
    }
  }

  /* ──────────────────────────────────────
     AUTO-ATTACH BUTTON STATES
     Binds to elements with data-fc-loading
     ────────────────────────────────────── */
  function bindAutoButtons() {
    document.querySelectorAll('[data-fc-loading]').forEach(function (el) {
      el.addEventListener('click', function () {
        setBtnLoading(el, true);
      });
    });
  }

  /* ──────────────────────────────────────
     INTERCEPT INTERNAL LINKS
     Show loader on same-origin navigation
     ────────────────────────────────────── */
  function bindNavIntercept() {
    document.addEventListener('click', function (e) {
      var link = e.target.closest('a');
      if (!link) return;

      var href = link.getAttribute('href');
      if (!href) return;

      /* Skip anchors, javascript:, tel:, mailto:, blank target, modifiers */
      if (href.charAt(0) === '#' || href.indexOf('javascript:') === 0 ||
          href.indexOf('tel:') === 0 || href.indexOf('mailto:') === 0) return;
      if (link.target === '_blank' || e.ctrlKey || e.metaKey || e.shiftKey) return;

      /* Only same-origin */
      try {
        var url = new URL(href, window.location.origin);
        if (url.origin !== window.location.origin) return;
      } catch (err) { return; }

      /* Skip download links */
      if (link.hasAttribute('download')) return;

      showLoader();
    });
  }

  /* ──────────────────────────────────────
     GLOBAL API
     ────────────────────────────────────── */
  window.showLoader = showLoader;
  window.hideLoader = hideLoader;
  window.setBtnLoading = setBtnLoading;

  /* ──────────────────────────────────────
     BOOT
     ────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      init();
      bindAutoButtons();
      bindNavIntercept();
    });
  } else {
    init();
    bindAutoButtons();
    bindNavIntercept();
  }
})();
