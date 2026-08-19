/**
 * Location data service — fetches countries & states from Django API
 * backed by pycountry + nigeria_states_lgas.
 *
 * Provides: populateCountries(), populateStates(), setupCountryStateCascade()
 */
(function() {
  var _data = null;
  var _promise = null;

  function fetchLocations() {
    if (_data) return Promise.resolve(_data);
    if (_promise) return _promise;
    _promise = fetch('/api/locations/')
      .then(function(r) { return r.json(); })
      .then(function(json) {
        _data = {};
        (json.countries || []).forEach(function(c) {
          _data[c.name] = c.states || [];
        });
        return _data;
      })
      .catch(function() {
        _data = {};
        return _data;
      });
    return _promise;
  }

  function populateCountries(countrySelect, currentValue) {
    if (!countrySelect) return;
    fetchLocations().then(function(data) {
      countrySelect.innerHTML = '';
      Object.keys(data).forEach(function(c) {
        var o = document.createElement('option');
        o.value = c;
        o.textContent = c;
        countrySelect.appendChild(o);
      });
      if (currentValue && data[currentValue]) {
        countrySelect.value = currentValue;
      }
    });
  }

  function populateStates(country, stateSelect, currentValue) {
    if (!stateSelect) return;
    stateSelect.innerHTML = '';
    fetchLocations().then(function(data) {
      var states = data[country] || [];
      if (states.length === 0) {
        var opt = document.createElement('option');
        opt.value = '';
        opt.textContent = '-- No states available --';
        opt.disabled = true;
        stateSelect.appendChild(opt);
        return;
      }
      var defaultOpt = document.createElement('option');
      defaultOpt.value = '';
      defaultOpt.textContent = 'Select State / Region';
      defaultOpt.disabled = true;
      stateSelect.appendChild(defaultOpt);
      states.forEach(function(s) {
        var o = document.createElement('option');
        o.value = s;
        o.textContent = s;
        stateSelect.appendChild(o);
      });
      if (currentValue && states.indexOf(currentValue) !== -1) {
        stateSelect.value = currentValue;
      } else {
        stateSelect.selectedIndex = 0;
      }
    });
  }

  function setupCountryStateCascade(countryId, stateId, currentStateValue, currentCountryValue) {
    var countryEl = document.getElementById(countryId);
    var stateEl = document.getElementById(stateId);
    if (!countryEl || !stateEl) return;

    fetchLocations().then(function() {
      if (currentCountryValue) countryEl.value = currentCountryValue;
      populateStates(countryEl.value, stateEl, currentStateValue);
    });

    countryEl.addEventListener('change', function() {
      populateStates(this.value, stateEl, '');
    });
  }

  window.populateCountries = populateCountries;
  window.populateStates = populateStates;
  window.setupCountryStateCascade = setupCountryStateCascade;
})();
