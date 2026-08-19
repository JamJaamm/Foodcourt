/**
 * Location data service — fetches countries, states & LGAs from Django API
 * backed by pycountry + nigeria_states_lgas.
 *
 * Provides: populateCountries(), populateStates(), populateLGAs(),
 *           setupCountryStateCascade(), setupStateLGACascade()
 */
(function() {
  var _data = null;
  var _promise = null;
  var _ngLgas = {};

  function fetchLocations() {
    if (_data) return Promise.resolve(_data);
    if (_promise) return _promise;
    _promise = fetch('/api/locations/')
      .then(function(r) { return r.json(); })
      .then(function(json) {
        _data = {};
        _ngLgas = {};
        (json.countries || []).forEach(function(c) {
          if (c.name === 'Nigeria') {
            var stateNames = [];
            (c.states || []).forEach(function(s) {
              if (typeof s === 'object') {
                stateNames.push(s.name);
                _ngLgas[s.name] = s.lgas || [];
              } else {
                stateNames.push(s);
              }
            });
            _data['Nigeria'] = stateNames;
          } else {
            _data[c.name] = c.states || [];
          }
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
    if (!countrySelect) return Promise.resolve();
    return fetchLocations().then(function(data) {
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
    if (!stateSelect) return Promise.resolve();
    stateSelect.innerHTML = '<option value="" disabled selected>Loading...</option>';
    return fetchLocations().then(function(data) {
      var states = data[country] || [];
      stateSelect.innerHTML = '';
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

  function populateLGAs(state, lgaSelect, currentValue) {
    if (!lgaSelect) return Promise.resolve();
    lgaSelect.innerHTML = '<option value="" disabled selected>Loading...</option>';
    return fetchLocations().then(function() {
      var lgas = _ngLgas[state] || [];
      lgaSelect.innerHTML = '';
      if (lgas.length === 0) {
        var opt = document.createElement('option');
        opt.value = '';
        opt.textContent = '-- No LGAs available --';
        opt.disabled = true;
        lgaSelect.appendChild(opt);
        return;
      }
      var defaultOpt = document.createElement('option');
      defaultOpt.value = '';
      defaultOpt.textContent = 'Select LGA';
      defaultOpt.disabled = true;
      lgaSelect.appendChild(defaultOpt);
      lgas.forEach(function(l) {
        var o = document.createElement('option');
        o.value = l;
        o.textContent = l;
        lgaSelect.appendChild(o);
      });
      if (currentValue && lgas.indexOf(currentValue) !== -1) {
        lgaSelect.value = currentValue;
      } else {
        lgaSelect.selectedIndex = 0;
      }
    });
  }

  function setupCountryStateCascade(countryId, stateId, currentStateValue, currentCountryValue) {
    var countryEl = document.getElementById(countryId);
    var stateEl = document.getElementById(stateId);
    if (!countryEl || !stateEl) return;

    populateCountries(countryEl, currentCountryValue).then(function() {
      populateStates(countryEl.value, stateEl, currentStateValue);
    });

    countryEl.addEventListener('change', function() {
      populateStates(this.value, stateEl, '');
    });
  }

  function setupStateLGACascade(stateId, lgaId, currentLgaValue, currentStateValue) {
    var stateEl = document.getElementById(stateId);
    var lgaEl = document.getElementById(lgaId);
    if (!stateEl || !lgaEl) return;

    if (currentStateValue) {
      populateLGAs(currentStateValue, lgaEl, currentLgaValue);
    }

    stateEl.addEventListener('change', function() {
      populateLGAs(this.value, lgaEl, '');
    });
  }

  window.populateCountries = populateCountries;
  window.populateStates = populateStates;
  window.populateLGAs = populateLGAs;
  window.setupCountryStateCascade = setupCountryStateCascade;
  window.setupStateLGACascade = setupStateLGACascade;
})();
