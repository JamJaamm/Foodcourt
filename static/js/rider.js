/* ============================================================
   Choply — Rider Landing / Registration Modal (rider.js)
   ============================================================ */
'use strict';

const RIDER_STATE = {
  step: 1,
  total: 6,
  avatar: null,
  uploads: {}
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DIGITS_RE = /^\d{10}$/;

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initDrawer();
  initReveal();
  initAccordion();
  initPasswordToggles();
  initAvatarUpload();
  initDropzones();
  initModalKeyboard();
  initBankVerification();
  initLoginPage();
});

/* ══════════════════════════════════════════════
   STICKY NAV
   ══════════════════════════════════════════════ */
function initNav() {
  const nav = document.getElementById('rdrNav');
  if (!nav) return;
  const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 12);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
}

/* ══════════════════════════════════════════════
   MOBILE DRAWER
   ══════════════════════════════════════════════ */
function initDrawer() {
  const toggle = document.getElementById('rdrNavToggle');
  if (toggle) toggle.addEventListener('click', () => window.openRiderDrawer());
}

window.openRiderDrawer = () => {
  const drawer = document.getElementById('rdrDrawer');
  if (drawer) drawer.classList.add('open');
};

window.closeRiderDrawer = () => {
  const drawer = document.getElementById('rdrDrawer');
  if (drawer) drawer.classList.remove('open');
};

/* ══════════════════════════════════════════════
   SCROLL REVEAL
   ══════════════════════════════════════════════ */
function initReveal() {
  const targets = document.querySelectorAll('[data-rdr-reveal]');
  if (targets.length === 0) return;

  if (!('IntersectionObserver' in window)) {
    targets.forEach(el => el.classList.add('rdr-in'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('rdr-in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  targets.forEach(el => observer.observe(el));
}

/* ══════════════════════════════════════════════
   FAQ ACCORDION (single open)
   ══════════════════════════════════════════════ */
function initAccordion() {
  const items = document.querySelectorAll('.rdr-accordion-item');
  items.forEach(item => {
    const head = item.querySelector('.rdr-acc-head');
    const body = item.querySelector('.rdr-acc-body');
    if (!head || !body) return;

    head.addEventListener('click', () => {
      const isOpen = item.classList.contains('active');

      items.forEach(other => {
        other.classList.remove('active');
        const b = other.querySelector('.rdr-acc-body');
        if (b) b.style.maxHeight = null;
      });

      if (!isOpen) {
        item.classList.add('active');
        body.style.maxHeight = body.scrollHeight + 'px';
      }
    });
  });
}

/* ══════════════════════════════════════════════
   PASSWORD TOGGLES
   ══════════════════════════════════════════════ */
function initPasswordToggles() {
  document.querySelectorAll('[data-pw-toggle]').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.getAttribute('data-pw-toggle'));
      if (!input) return;
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      const icon = btn.querySelector('i');
      if (icon) icon.className = show ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
    });
  });
}

/* ══════════════════════════════════════════════
   PAYSTACK BANK VERIFICATION (step 5)
   ══════════════════════════════════════════════ */
function initBankVerification() {
  const bankSelect = document.getElementById('rdrBankName');
  const acctNo = document.getElementById('rdrAcctNo');
  const acctName = document.getElementById('rdrAcctName');
  const hint = document.getElementById('rdrBankHint');
  if (!bankSelect || !acctNo || !acctName) return;

  let resolveTimer = null;
  let banksLoaded = false;

  function setHint(text, type) {
    if (!hint) return;
    hint.textContent = text || '';
    hint.className = 'rdr-bank-hint' + (type ? ' ' + type : '');
  }

  function clearAccount() {
    acctName.value = '';
    setFieldError('rdrAcctName', true);
    setHint('');
  }

  function loadBanks() {
    if (banksLoaded) return;

    bankSelect.innerHTML = '<option value="" selected disabled>Loading banks…</option>';

    fetch('/riders/api/banks/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.json().then(data => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (!ok || !data || !Array.isArray(data.banks)) {
          bankSelect.innerHTML = '<option value="" selected disabled>Could not load banks — tap to retry</option>';
          return;
        }
        if (!data.banks.length) {
          bankSelect.innerHTML = '<option value="" selected disabled>No banks available</option>';
          banksLoaded = true;
          return;
        }
        banksLoaded = true;
        bankSelect.innerHTML = '<option value="" selected disabled>Select your bank</option>';
        data.banks.forEach(b => {
          const opt = document.createElement('option');
          opt.value = b.code;
          opt.textContent = b.name;
          bankSelect.appendChild(opt);
        });
      })
      .catch(() => {
        bankSelect.innerHTML = '<option value="" selected disabled>Could not load banks — tap to retry</option>';
      });
  }

  function resolveAccount() {
    const bank = bankSelect.value;
    const no = acctNo.value.trim();
    if (!bank || !DIGITS_RE.test(no)) return;

    acctName.value = '';
    setFieldError('rdrAcctName', true);
    setHint('Verifying account…', 'loading');

    fetch('/riders/api/banks/resolve/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({ bank_code: bank, account_number: no })
    })
      .then(r => r.json().then(data => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (ok && data.ok && data.account_name) {
          acctName.value = data.account_name;
          setFieldError('rdrAcctName', false);
          setHint('Account verified', 'success');
        } else {
          acctName.value = '';
          setFieldError('rdrAcctName', true);
          setHint((data && data.error) || 'Account could not be verified.', 'error');
        }
      })
      .catch(() => {
        acctName.value = '';
        setFieldError('rdrAcctName', true);
        setHint('Account could not be verified. Please try again.', 'error');
      });
  }

  bankSelect.addEventListener('click', loadBanks);
  bankSelect.addEventListener('change', () => {
    clearAccount();
    if (acctNo.value.trim().length === 10) resolveAccount();
  });

  acctNo.addEventListener('input', () => {
    clearAccount();
    clearTimeout(resolveTimer);
    if (acctNo.value.trim().length === 10 && bankSelect.value) {
      resolveTimer = setTimeout(resolveAccount, 600);
    }
  });

  window.loadRiderBanks = loadBanks;
}

/* ══════════════════════════════════════════════
   MODAL OPEN / CLOSE / RESET
   ══════════════════════════════════════════════ */
window.openRiderRegister = () => {
  const modal = document.getElementById('rdrRegisterModal');
  if (!modal) return;
  resetRiderModal();
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  if (window.loadRiderBanks) window.loadRiderBanks();
};

window.closeRiderRegister = () => {
  const modal = document.getElementById('rdrRegisterModal');
  if (!modal) return;
  modal.classList.remove('open');
  document.body.style.overflow = '';
};

function initModalKeyboard() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      window.closeRiderRegister();
      window.closeRiderDrawer();
    }
  });
}

function resetRiderModal() {
  RIDER_STATE.step = 1;
  RIDER_STATE.avatar = null;
  RIDER_STATE.uploads = {};

  const form = document.getElementById('rdrForm');
  if (form) form.reset();

  const success = document.getElementById('rdrSuccess');
  if (success) success.classList.remove('show');

  const head = document.querySelector('.rdr-modal-head');
  const progress = document.getElementById('rdrProgressWrap');
  const foot = document.querySelector('.rdr-modal-foot');
  if (head) head.style.display = '';
  if (progress) progress.style.display = '';
  if (form) form.style.display = '';
  if (foot) foot.style.display = '';

  document.querySelectorAll('.rdr-field-error').forEach(el => el.classList.remove('show'));
  document.querySelectorAll('.rdr-input.invalid, .rdr-select.invalid').forEach(el => el.classList.remove('invalid'));

  const errorBox = document.getElementById('rdrRegisterError');
  if (errorBox) {
    errorBox.textContent = '';
    errorBox.classList.remove('show');
  }

  const avatar = document.getElementById('rdrAvatarPreview');
  if (avatar) avatar.innerHTML = '<i class="fa-solid fa-user"></i>';

  const uploadList = document.getElementById('rdrUploadList');
  if (uploadList) uploadList.innerHTML = '';

  const bankHint = document.getElementById('rdrBankHint');
  if (bankHint) bankHint.textContent = '';

  showRiderStep(1);
}

/* ══════════════════════════════════════════════
   WIZARD NAVIGATION
   ══════════════════════════════════════════════ */
window.rdrStep = (dir) => {
  const next = dir === 'next' ? RIDER_STATE.step + 1 : RIDER_STATE.step - 1;

  if (dir === 'next' && !validateRiderStep(RIDER_STATE.step)) return;

  if (next > RIDER_STATE.total) {
    submitRiderApplication();
    return;
  }

  RIDER_STATE.step = Math.max(1, Math.min(next, RIDER_STATE.total));
  showRiderStep(RIDER_STATE.step);
};

function showRiderStep(step) {
  document.querySelectorAll('.rdr-step-panel').forEach(panel => {
    panel.classList.toggle('active', parseInt(panel.getAttribute('data-step'), 10) === step);
  });

  const fill = document.getElementById('rdrProgressFill');
  if (fill) fill.style.width = (step / RIDER_STATE.total * 100) + '%';

  const labels = document.querySelectorAll('#rdrProgressSteps span');
  labels.forEach((label, idx) => {
    const n = idx + 1;
    label.classList.toggle('done', n < step);
    label.classList.toggle('now', n === step);
  });

  const hint = document.getElementById('rdrStepHint');
  if (hint) hint.textContent = 'Step ' + step + ' of ' + RIDER_STATE.total;

  const prev = document.getElementById('rdrPrevBtn');
  if (prev) prev.style.visibility = step === 1 ? 'hidden' : 'visible';

  const nextBtn = document.getElementById('rdrNextBtn');
  if (nextBtn) {
    if (step === RIDER_STATE.total) {
      nextBtn.innerHTML = '<i class="fa-solid fa-paper-plane me-1"></i> Submit Application';
    } else {
      nextBtn.innerHTML = 'Continue <i class="fa-solid fa-arrow-right ms-1"></i>';
    }
  }

  if (step === RIDER_STATE.total) {
    fillReviewSummary();
  }

  const body = document.getElementById('rdrModalBody');
  if (body) body.scrollTop = 0;
}

/* ══════════════════════════════════════════════
   FIELD VALIDATION HELPERS
   ══════════════════════════════════════════════ */
function setFieldError(key, invalid) {
  const error = document.querySelector(`[data-error-for="${key}"]`);
  if (error) error.classList.toggle('show', invalid);
  const input = document.getElementById(key);
  if (input) input.classList.toggle('invalid', invalid);
}

function isEmailValid(value) {
  return EMAIL_RE.test(value);
}

function isPhoneValid(value) {
  return (value.match(/\d/g) || []).length >= 7;
}

function isDobValid(value) {
  if (!value) return false;
  const age = (Date.now() - new Date(value).getTime()) / (365.25 * 24 * 3600 * 1000);
  return age >= 18 && age < 120;
}

function validateRiderStep(step) {
  switch (step) {
    case 1: {
      const avatarOk = !!RIDER_STATE.avatar;
      const fname = fieldValue('rdrFname');
      const lname = fieldValue('rdrLname');
      const email = fieldValue('rdrEmail');
      const phone = fieldValue('rdrPhone');
      const pw = fieldValue('rdrPw');
      const pw2 = fieldValue('rdrPw2');
      const dob = fieldValue('rdrDob');

      setFieldError('avatar', !avatarOk);
      setFieldError('rdrFname', !fname);
      setFieldError('rdrLname', !lname);
      setFieldError('rdrEmail', !isEmailValid(email));
      setFieldError('rdrPhone', !isPhoneValid(phone));
      setFieldError('rdrPw', pw.length < 8);
      setFieldError('rdrPw2', pw2 === '' || pw2 !== pw);
      setFieldError('rdrDob', !isDobValid(dob));

      return avatarOk && fname && lname && isEmailValid(email) && isPhoneValid(phone) &&
             pw.length >= 8 && pw2 === pw && isDobValid(dob);
    }
    case 2: {
      const address = fieldValue('rdrAddress');
      const city = fieldValue('rdrCity');
      const state = fieldValue('rdrState');
      const country = fieldValue('rdrCountry');

      setFieldError('rdrAddress', !address);
      setFieldError('rdrCity', !city);
      setFieldError('rdrState', !state);
      setFieldError('rdrCountry', !country);

      return !!(address && city && state && country);
    }
    case 3: {
      const type = fieldValue('rdrVehicleType');
      const brand = fieldValue('rdrBrand');
      const model = fieldValue('rdrModel');
      const color = fieldValue('rdrColor');
      const plate = fieldValue('rdrPlate');

      setFieldError('rdrVehicleType', !type);
      setFieldError('rdrBrand', !brand);
      setFieldError('rdrModel', !model);
      setFieldError('rdrColor', !color);
      setFieldError('rdrPlate', !plate);

      return !!(type && brand && model && color && plate);
    }
    case 4: {
      const gov = !!RIDER_STATE.uploads['gov-id'];
      const license = !!RIDER_STATE.uploads['drivers-license'];

      setFieldError('gov-id', !gov);
      setFieldError('drivers-license', !license);

      return gov && license;
    }
    case 5: {
      const bank = fieldValue('rdrBankName');
      const acctName = fieldValue('rdrAcctName');
      const acctNo = fieldValue('rdrAcctNo');

      setFieldError('rdrBankName', !bank);
      setFieldError('rdrAcctName', !acctName);
      setFieldError('rdrAcctNo', !DIGITS_RE.test(acctNo));

      return !!(bank && acctName && DIGITS_RE.test(acctNo));
    }
    default:
      return true;
  }
}

function fieldValue(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

/* ══════════════════════════════════════════════
   AVATAR UPLOAD
   ══════════════════════════════════════════════ */
function initAvatarUpload() {
  const input = document.getElementById('rdrAvatarFile');
  if (!input) return;

  input.addEventListener('change', () => {
    const file = input.files && input.files[0];
    if (!file) return;
    RIDER_STATE.avatar = file;

    const preview = document.getElementById('rdrAvatarPreview');
    if (preview) {
      if (preview.querySelector('img')) {
        preview.querySelector('img').src = URL.createObjectURL(file);
      } else {
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        preview.innerHTML = '';
        preview.appendChild(img);
      }
    }

    setFieldError('avatar', false);
  });
}

/* ══════════════════════════════════════════════
   DROPZONE SIMULATED UPLOADS
   ══════════════════════════════════════════════ */
function initDropzones() {
  document.querySelectorAll('.rdr-dropzone[data-dropzone]').forEach(dz => {
    const input = dz.querySelector('input[type="file"]');
    if (!input) return;
    const key = dz.getAttribute('data-dropzone');

    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) return;
      addUploadItem(key, file);
    });
  });
}

function addUploadItem(key, file) {
  RIDER_STATE.uploads[key] = file;
  setFieldError(key, false);

  const list = document.getElementById('rdrUploadList');
  if (!list) return;

  const item = document.createElement('div');
  item.className = 'rdr-upload-item';
  item.innerHTML = `
    <img class="thumb" alt="" src="">
    <div class="info">
      <div class="nm">${escapeHtml(file.name)}</div>
      <div class="st">Uploading…</div>
      <div class="rdr-upload-bar"><i></i></div>
    </div>
    <button type="button" class="del" aria-label="Remove"><i class="fa-solid fa-trash-can"></i></button>
  `;

  const thumb = item.querySelector('.thumb');
  if (file.type.startsWith('image/')) {
    thumb.src = URL.createObjectURL(file);
  } else {
    thumb.style.background = 'var(--rdr-green-subtle)';
    thumb.style.display = 'grid';
    thumb.style.placeItems = 'center';
    thumb.alt = 'PDF';
    thumb.outerHTML = '<div class="thumb" style="display:grid;place-items:center;background:var(--rdr-green-subtle);color:var(--rdr-green-dark);font-weight:700;">PDF</div>';
  }

  item.querySelector('.del').addEventListener('click', () => {
    delete RIDER_STATE.uploads[key];
    item.remove();
    const dz = document.querySelector(`.rdr-dropzone[data-dropzone="${key}"] input[type="file"]`);
    if (dz) dz.value = '';
    if (key === 'gov-id' || key === 'drivers-license') setFieldError(key, true);
  });

  list.appendChild(item);

  const bar = item.querySelector('.rdr-upload-bar i');
  const status = item.querySelector('.st');
  let progress = 0;
  const timer = setInterval(() => {
    progress += Math.ceil(Math.random() * 18);
    if (progress >= 100) {
      progress = 100;
      clearInterval(timer);
      item.classList.add('done');
      status.textContent = 'Uploaded';
    }
    if (bar) bar.style.width = progress + '%';
  }, 160);
}

function escapeHtml(value) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ══════════════════════════════════════════════
   REVIEW SUMMARY + SUBMIT
   ══════════════════════════════════════════════ */
function fillReviewSummary() {
  const value = (id) => fieldValue(id) || '—';
  const bankSelect = document.getElementById('rdrBankName');
  const bankName = bankSelect && bankSelect.options[bankSelect.selectedIndex]
    ? bankSelect.options[bankSelect.selectedIndex].text
    : '';
  const map = {
    'name': fieldValue('rdrFname') + ' ' + fieldValue('rdrLname'),
    'email': value('rdrEmail'),
    'phone': value('rdrPhone'),
    'dob': value('rdrDob'),
    'address': value('rdrAddress'),
    'city': fieldValue('rdrCity') + ', ' + fieldValue('rdrState'),
    'country': value('rdrCountry'),
    'zip': value('rdrZip') || '—',
    'vehicle': value('rdrVehicleType'),
    'vehicleDetail': fieldValue('rdrBrand') + ' / ' + fieldValue('rdrModel'),
    'color': value('rdrColor'),
    'plate': value('rdrPlate'),
    'bank': bankName || '—',
    'acctName': value('rdrAcctName'),
    'acctNo': value('rdrAcctNo')
  };

  Object.keys(map).forEach(key => {
    const el = document.querySelector(`[data-summ="${key}"]`);
    if (el) el.textContent = map[key];
  });
}

function submitRiderApplication() {
  fillReviewSummary();

  const nextBtn = document.getElementById('rdrNextBtn');
  if (nextBtn) {
    nextBtn.disabled = true;
    nextBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Submitting…';
  }

  const fd = new FormData();
  const payload = buildRiderPayload();
  Object.keys(payload).forEach(key => fd.append(key, payload[key]));
  if (RIDER_STATE.avatar) fd.append('avatar_file', RIDER_STATE.avatar);
  Object.keys(RIDER_STATE.uploads).forEach(key => fd.append('documents_files', RIDER_STATE.uploads[key]));

  fetch('/riders/register/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: fd
  })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(({ ok, data }) => {
      if (!ok) {
        const msg = (data && data.errors && Object.values(data.errors)[0]) || 'Registration failed. Please try again.';
        throw new Error(msg);
      }
      showRiderSuccess();
    })
    .catch(error => {
      showRiderSubmitError(error.message);
      if (nextBtn) {
        nextBtn.disabled = false;
        nextBtn.innerHTML = '<i class="fa-solid fa-paper-plane me-1"></i> Submit Application';
      }
    });
}

function buildRiderPayload() {
  const val = (id) => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  };
  const pw = document.getElementById('rdrPw');

  const bankSelect = document.getElementById('rdrBankName');
  const bankName = bankSelect && bankSelect.options[bankSelect.selectedIndex]
    ? bankSelect.options[bankSelect.selectedIndex].text
    : '';

  return {
    first_name: val('rdrFname'),
    last_name: val('rdrLname'),
    email: val('rdrEmail'),
    phone: val('rdrPhone'),
    password: pw ? pw.value : '',
    dob: val('rdrDob'),
    avatar: RIDER_STATE.avatar ? RIDER_STATE.avatar.name : '',
    address: val('rdrAddress'),
    city: val('rdrCity'),
    state: val('rdrState'),
    country: val('rdrCountry'),
    postal_code: val('rdrZip'),
    vehicle_type: val('rdrVehicleType'),
    vehicle_brand: val('rdrBrand'),
    vehicle_model: val('rdrModel'),
    vehicle_color: val('rdrColor'),
    vehicle_plate: val('rdrPlate'),
    bank_name: bankName,
    bank_code: val('rdrBankName'),
    account_name: val('rdrAcctName'),
    account_number: val('rdrAcctNo'),
    documents: Object.keys(RIDER_STATE.uploads).map(key => RIDER_STATE.uploads[key].name).join(', ')
  };
}

function showRiderSuccess() {
  const form = document.getElementById('rdrForm');
  const head = document.querySelector('.rdr-modal-head');
  const progress = document.getElementById('rdrProgressWrap');
  const foot = document.querySelector('.rdr-modal-foot');
  const success = document.getElementById('rdrSuccess');

  if (head) head.style.display = 'none';
  if (progress) progress.style.display = 'none';
  if (form) form.style.display = 'none';
  if (foot) foot.style.display = 'none';
  if (success) success.classList.add('show');
}

function showRiderSubmitError(message) {
  const box = document.getElementById('rdrRegisterError');
  if (box) {
    box.textContent = message;
    box.classList.add('show');
  }
}

function getCookie(name) {
  let value = null;
  if (document.cookie && document.cookie !== '') {
    document.cookie.split(';').forEach(c => {
      c = c.trim();
      if (c.substring(0, name.length + 1) === (name + '=')) {
        value = decodeURIComponent(c.substring(name.length + 1));
      }
    });
  }
  return value;
}

/* ══════════════════════════════════════════════
   RIDER LOGIN PAGE (password toggle + inline error)
   ══════════════════════════════════════════════ */
function initLoginPage() {
  const loginForm = document.getElementById('rdrLoginForm');
  if (!loginForm) return;

  loginForm.addEventListener('submit', (e) => {
    const email = document.getElementById('rdrLoginEmail');
    const emailValue = email ? email.value.trim() : '';
    if (!EMAIL_RE.test(emailValue)) {
      e.preventDefault();
      const errorBox = document.getElementById('rdrLoginError');
      if (errorBox) {
        errorBox.textContent = 'Please enter a valid email address.';
        errorBox.classList.add('show');
      }
      if (email) email.classList.add('invalid');
    }
  });
}
