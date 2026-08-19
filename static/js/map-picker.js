/**
 * LocationPicker — Reusable Leaflet map + browser geolocation module.
 *
 * Provides:
 *   LocationPicker.open(config)            — inline interactive map with draggable marker
 *   LocationPicker.getCurrentLocation(config) — browser Geolocation API
 *
 * Usage from a template:
 *   <script src="{% static 'js/map-picker.js' %}"></script>
 *   LocationPicker.open({ containerId: 'my-map', latInputId: 'lat', ... });
 */
(function () {
  'use strict';

  var _activeMap = null;
  var _activeMarker = null;
  var _activeContainerId = null;

  /* ─── Nigerian state approximate centres ─── */
  var _stateCenters = {
    'Lagos': [6.5244, 3.3792],
    'Ogun': [7.1560, 3.3476],
    'Oyo': [7.3964, 3.9167],
    'Rivers': [4.7982, 7.0064],
    'Abuja': [9.0579, 7.4951],
    'FCT': [9.0579, 7.4951],
    'Kano': [12.0022, 8.5920],
    'Kaduna': [10.5264, 7.4342],
    'Delta': [5.5167, 5.7500],
    'Enugu': [6.4413, 7.4988],
    'Anambra': [6.2100, 6.9960],
    'Abia': [5.1066, 7.3668],
    'Edo': [6.3350, 5.6270],
    'Osun': [7.7667, 4.5667],
    'Ondo': [7.2500, 5.1950],
    'Ekiti': [7.6211, 5.2214],
    'Plateau': [9.9167, 8.9000],
    'Cross River': [5.9500, 8.3250],
    'Akwa Ibom': [5.0333, 7.9167],
    'Benue': [7.3333, 8.7500],
    'Kogi': [7.7964, 6.7400],
    'Nasarawa': [8.3000, 8.3000],
    'Taraba': [7.8700, 10.7800],
    'Borno': [11.8464, 13.1603],
    'Yobe': [11.7500, 11.9667],
    'Gombe': [10.2900, 11.1700],
    'Bauchi': [10.3100, 9.8400],
    'Sokoto': [13.0600, 5.2400],
    'Zamfara': [12.1700, 6.6600],
    'Kebbi': [11.4900, 4.2300],
    'Niger': [9.6100, 6.5600],
    'Kwara': [8.5000, 4.5500],
  };

  var _defaultCenter = [6.5244, 3.3792]; // Lagos

  function _getStateCenter(state) {
    if (!state) return _defaultCenter;
    var trimmed = state.trim();
    if (_stateCenters[trimmed]) return _stateCenters[trimmed];
    return _defaultCenter;
  }

  /* ─── DOM helpers ─── */
  function _el(id) { return document.getElementById(id); }

  function _setVal(inputId, val) {
    var el = _el(inputId);
    if (el) el.value = val;
  }

  function _showStatus(statusId, html, color) {
    var el = _el(statusId);
    if (!el) return;
    el.style.display = 'block';
    el.style.color = color;
    el.innerHTML = html;
  }

  function _showBadge(badgeId, html) {
    var el = _el(badgeId);
    if (!el) return;
    el.innerHTML = html;
  }

  function _hideActions(actionsId) {
    var el = _el(actionsId);
    if (el) el.style.display = 'none';
  }

  function _showActions(actionsId) {
    var el = _el(actionsId);
    if (el) el.style.display = 'flex';
  }

  /* ─── Default icon (no shadow, compact marker) ─── */
  function _defaultIcon() {
    return L.divIcon({
      className: 'fc-map-marker',
      html: '<div style="width:28px;height:28px;background:var(--primary,#FF6B35);border:3px solid #fff;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 2px 8px rgba(0,0,0,.35);"></div>',
      iconSize: [28, 28],
      iconAnchor: [14, 28],
      popupAnchor: [0, -30],
    });
  }

  function _confirmHtml(lat, lng) {
    return '<span style="font-size:11px;color:var(--rdr-green,#06D6A0);background:rgba(6,214,160,.12);padding:2px 8px;border-radius:10px;"><i class="fa-solid fa-check-circle me-1"></i>Location selected</span>';
  }

  function _warningHtml(text) {
    return '<span style="font-size:11px;color:#f9a825;background:rgba(249,168,37,.12);padding:2px 8px;border-radius:10px;"><i class="fa-solid fa-exclamation-circle me-1"></i>' + (text || 'Not selected') + '</span>';
  }

  function _errorHtml(text) {
    return '<span style="font-size:11px;color:var(--danger,#ef4444);background:rgba(239,68,68,.1);padding:2px 8px;border-radius:10px;"><i class="fa-solid fa-circle-exclamation me-1"></i>' + text + '</span>';
  }

  /* ─── Destroy existing map if any ─── */
  function _destroyMap() {
    if (_activeMap) {
      _activeMap.remove();
      _activeMap = null;
      _activeMarker = null;
      _activeContainerId = null;
    }
  }

  /* ════════════════════════════════════════════════
     PUBLIC: open(config)
     ════════════════════════════════════════════════ */
  function openMap(config) {
    if (typeof L === 'undefined') {
      _showStatus(config.statusId, '<i class="fa-solid fa-circle-exclamation me-1"></i> Map library failed to load. Please try again.', 'var(--danger,#ef4444)');
      return;
    }

    _destroyMap();

    var container = _el(config.containerId);
    if (!container) return;

    container.style.display = 'block';
    container.style.width = '100%';
    container.style.height = '280px';
    container.style.borderRadius = '12px';
    container.style.overflow = 'hidden';
    container.style.border = '1px solid var(--border,#e2e8f0)';

    // Determine initial center
    var initLat = config.defaultLat || null;
    var initLng = config.defaultLng || null;
    var center;
    if (initLat && initLng) {
      center = [parseFloat(initLat), parseFloat(initLng)];
    } else {
      center = _getStateCenter(config.state);
    }

    // Create map
    var map = L.map(container, {
      center: center,
      zoom: initLat ? 15 : 12,
      zoomControl: true,
      attributionControl: true,
    });

    // Add tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    // Add marker
    var marker = L.marker(center, { icon: _defaultIcon(), draggable: true }).addTo(map);

    // Click on map moves marker
    map.on('click', function (e) {
      marker.setLatLng(e.latlng);
    });

    // Store references
    _activeMap = map;
    _activeMarker = marker;
    _activeContainerId = config.containerId;

    // Fix tile rendering inside containers that were hidden
    setTimeout(function () { map.invalidateSize(); }, 100);

    // Build button row
    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:8px;margin-top:10px;align-items:center;';

    var confirmBtn = document.createElement('button');
    confirmBtn.type = 'button';
    confirmBtn.className = 'fc-btn fc-btn-primary fc-btn-sm';
    confirmBtn.innerHTML = '<i class="fa-solid fa-check me-1"></i> Confirm Location';
    confirmBtn.style.cssText = 'font-size:12px;padding:6px 14px;';
    confirmBtn.onclick = function () {
      var ll = marker.getLatLng();
      var lat = ll.lat.toFixed(6);
      var lng = ll.lng.toFixed(6);

      _setVal(config.latInputId, lat);
      _setVal(config.lngInputId, lng);

      _showStatus(config.statusId, '<i class="fa-solid fa-circle-check me-1"></i> <strong>Location confirmed!</strong>', 'var(--rdr-green,#06D6A0)');
      _showBadge(config.badgeId, _confirmHtml(lat, lng));
      _destroyMap();
      container.style.display = 'none';

      if (typeof Toast !== 'undefined') Toast.show('Location confirmed!', 'success');
      if (typeof config.onConfirm === 'function') config.onConfirm(lat, lng);
    };

    var cancelLink = document.createElement('button');
    cancelLink.type = 'button';
    cancelLink.className = 'fc-btn fc-btn-outline fc-btn-sm';
    cancelLink.innerHTML = '<i class="fa-solid fa-xmark me-1"></i> Cancel';
    cancelLink.style.cssText = 'font-size:12px;padding:6px 14px;';
    cancelLink.onclick = function () {
      _destroyMap();
      container.style.display = 'none';
      _showActions(config.actionsId);
    };

    btnRow.appendChild(confirmBtn);
    btnRow.appendChild(cancelLink);
    container.parentNode.insertBefore(btnRow, container.nextSibling);

    // Store btnRow ref for cleanup
    container._btnRow = btnRow;

    // Hide the action buttons while map is open
    var actionsEl = _el(config.actionsId);
    if (actionsEl) actionsEl.style.display = 'none';
  }

  /* ════════════════════════════════════════════════
     PUBLIC: getCurrentLocation(config)
     ════════════════════════════════════════════════ */
  function getCurrentLocation(config) {
    if (!navigator.geolocation) {
      _showStatus(config.statusId, '<i class="fa-solid fa-circle-exclamation me-1"></i> Your browser doesn\'t support location services. Please select your location on the map.', 'var(--danger,#ef4444)');
      _showBadge(config.badgeId, _errorHtml('Unsupported'));
      return;
    }

    _showStatus(config.statusId, '<i class="fa-solid fa-spinner fa-spin me-1"></i> Detecting your location...', 'var(--text-secondary,#94a3b8)');
    _showBadge(config.badgeId, _warningHtml('Detecting...'));

    navigator.geolocation.getCurrentPosition(
      function (position) {
        var lat = position.coords.latitude.toFixed(6);
        var lng = position.coords.longitude.toFixed(6);

        _setVal(config.latInputId, lat);
        _setVal(config.lngInputId, lng);

        _showStatus(config.statusId, '<i class="fa-solid fa-circle-check me-1"></i> <strong>Current location detected!</strong>', 'var(--rdr-green,#06D6A0)');
        _showBadge(config.badgeId, _confirmHtml(lat, lng));

        if (typeof Toast !== 'undefined') Toast.show('Current location detected!', 'success');
        if (typeof config.onConfirm === 'function') config.onConfirm(lat, lng);
      },
      function (error) {
        var msg;
        switch (error.code) {
          case error.PERMISSION_DENIED:
            msg = 'Location permission was denied. You can select your location manually on the map.';
            break;
          case error.POSITION_UNAVAILABLE:
            msg = 'Unable to get your current location. Please try again or select on the map.';
            break;
          case error.TIMEOUT:
            msg = 'Location request timed out. Please try again or select on the map.';
            break;
          default:
            msg = 'Unable to get your current location. Please select your location on the map.';
        }
        _showStatus(config.statusId, '<i class="fa-solid fa-circle-exclamation me-1"></i> ' + msg, 'var(--danger,#ef4444)');
        _showBadge(config.badgeId, _warningHtml('Not selected'));
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  }

  /* ─── Expose globally ─── */
  window.LocationPicker = {
    open: openMap,
    getCurrentLocation: getCurrentLocation,
  };

})();
