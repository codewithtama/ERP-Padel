import http.client, urllib.parse, re, sys

HOST = '127.0.0.1'
PORT = 8001

conn = http.client.HTTPConnection(HOST, PORT, timeout=10)

def request(method, path, body=None, headers=None):
    conn.request(method, path, body=body, headers=headers or {})
    r = conn.getresponse()
    data = r.read().decode()
    return r.status, data, dict(r.getheaders())

# GET login page for CSRF
status, body, hdrs = request('GET', '/login/')
ck = hdrs.get('Set-Cookie', '')
m = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', body)
if not m:
    print("NO CSRF TOKEN"); sys.exit(1)
token = m.group(1)

# POST login
data = urllib.parse.urlencode({'username':'admin','password':'admin123','csrfmiddlewaretoken':token})
head = {'Content-Type':'application/x-www-form-urlencoded','Cookie':ck,'Referer':f'http://{HOST}:{PORT}/login/'}
status, body, hdrs = request('POST', '/login/', data, head)
if status in (301,302,303,307,308):
    ck = hdrs.get('Set-Cookie', ck)
    loc = hdrs.get('Location', '/dashboard/')
    status, body, hdrs = request('GET', loc, headers={'Cookie':ck})
    ck = hdrs.get('Set-Cookie', ck)
    print('Login OK, on', loc)

# GET dashboard
status, body, hdrs = request('GET', '/dashboard/', headers={'Cookie':ck})
print('Dashboard:', status)
if status == 500:
    for line in body.split('\n'):
        if 'rupiah' in line or 'TemplateSyntax' in line or 'Error' in line:
            print(line.strip()[:300])
elif status in (200, 302):
    print('OK' if status == 200 else 'Redirected')
    if status == 200:
        print(body[:2000])
else:
    print('Unexpected:', status)

conn.close()

