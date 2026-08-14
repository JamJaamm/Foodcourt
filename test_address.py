import requests, re, sys

BASE = 'http://127.0.0.1:8000'
s = requests.Session()

# 1. GET login page
r = s.get(BASE + '/login/')
print(f'Login page: {r.status_code}')
print(f'Cookies after login page GET: {dict(s.cookies)}')
m = re.search(r'csrfmiddlewaretoken.*?value="([^"]+)"', r.text)
csrf = m.group(1) if m else None
print(f'Form CSRF: {csrf[:20] if csrf else "NONE"}')

# 2. Login as test user
data = {'csrfmiddlewaretoken': csrf, 'email': 'test@foodcourt.com', 'password': 'test123'}
r = s.post(BASE + '/login/', data=data, allow_redirects=False)
print(f'Login POST: {r.status_code} -> {r.headers.get("Location","none")}')
print(f'Cookies after login: {dict(s.cookies)}')
if r.status_code == 200:
    m = re.search(r'alert[^>]*>(.*?)</div>', r.text, re.DOTALL)
    if m:
        inner = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        print(f'Login error: {inner}')
    else:
        print('No login error shown')

# 3. GET dashboard
r = s.get(BASE + '/dashboard/')
print(f'Dashboard: {r.status_code}')
print(f'Cookies after dashboard: {dict(s.cookies)}')

# 4. Try saving an address via API
csrf_cookie = s.cookies.get('csrftoken')
print(f'CSRF cookie: {csrf_cookie[:20] if csrf_cookie else "NONE"}')

payload = {
    'action': 'create',
    'label': 'Home',
    'street': '123 Test Street',
    'landmark': 'Near Park',
    'city': 'Test City',
    'state': 'Test State',
    'country': 'United States',
    'phone': '+15551234567',
}
headers = {'Content-Type': 'application/json', 'X-CSRFToken': csrf_cookie}
r = s.post(BASE + '/api/addresses/', json=payload, headers=headers)
print(f'Address API POST: {r.status_code}')
print(f'Response: {r.text[:300]}')
