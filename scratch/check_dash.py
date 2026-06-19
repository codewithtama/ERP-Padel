import urllib.request, urllib.parse, re

HOST = '127.0.0.1'
PORT = 8001

def test():
    # 1. Get CSRF token
    req = urllib.request.Request(f'http://{HOST}:{PORT}/login/')
    res = urllib.request.urlopen(req)
    cookie = res.headers.get('Set-Cookie')
    html = res.read().decode()
    
    m = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', html)
    if not m:
        print("CSRF token not found")
        return
    token = m.group(1)
    
    # 2. Login
    data = urllib.parse.urlencode({
        'username': 'admin',
        'password': 'admin123',
        'csrfmiddlewaretoken': token
    }).encode()
    
    req2 = urllib.request.Request(
        f'http://{HOST}:{PORT}/login/',
        data=data,
        headers={'Cookie': cookie, 'Referer': f'http://{HOST}:{PORT}/login/'}
    )
    res2 = urllib.request.urlopen(req2)
    cookie2 = res2.headers.get('Set-Cookie') or cookie
    
    # 3. GET dashboard
    req3 = urllib.request.Request(
        f'http://{HOST}:{PORT}/dashboard/',
        headers={'Cookie': cookie2}
    )
    try:
        res3 = urllib.request.urlopen(req3)
        print("STATUS:", res3.status)
        print("BODY (first 2000 chars):")
        print(res3.read().decode()[:2000])
    except urllib.error.HTTPError as e:
        print("HTTP ERROR:", e.code)
        print(e.read().decode())

if __name__ == '__main__':
    test()
