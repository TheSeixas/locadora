import http.client,json,os,socket,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
p=subprocess.Popen([sys.executable,'server.py'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'PORT':str(port)})
def req(method,path,body=None,cookie=None):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);headers={'Content-Type':'application/json'}
    if cookie:headers['Cookie']=cookie
    c.request(method,path,body=json.dumps(body) if body is not None else None,headers=headers);r=c.getresponse();data=r.read();sc=r.getheader('Set-Cookie');c.close();return r.status,data,sc
try:
    html=(root/'public'/'index.html').read_text(encoding='utf-8');js=(root/'public'/'app.js').read_text(encoding='utf-8');css=(root/'public'/'styles.css').read_text(encoding='utf-8')
    assert 'loginForm' in html and '/app.js' in html and '/styles.css' in html
    assert "addEventListener('submit'" in js and 'e.preventDefault()' in js and '/api/auth/login' in js
    assert '--accent:' in css and '.movie-grid' in css and '@media' in css and ':focus-visible' in css
    for _ in range(40):
        try: status,_,_=req('GET','/');assert status==200;break
        except Exception:time.sleep(.1)
    else:raise RuntimeError('SERVER_NOT_READY')
    for asset in ('/app.js','/styles.css'):status,_,_=req('GET',asset);assert status==200,f'{asset}:{status}'
    status,_,_=req('GET','/api/catalog');assert status==401,status
    status,_,sc=req('POST','/api/auth/login',{'username':'admin','password':'admin123'});assert status==200,status;cookie=sc.split(';',1)[0]
    status,data,_=req('GET','/api/catalog',cookie=cookie);assert status==200;payload=json.loads(data);assert len(payload['movies'])==5
    status,_,_=req('POST','/api/auth/login',{'username':'inativo','password':'inactive123'});assert status==403,status
    status,_,kid=req('POST','/api/auth/login',{'username':'crianca','password':'kids123'});assert status==200;kid=kid.split(';',1)[0]
    status,data,_=req('GET','/api/catalog',cookie=kid);assert status==200;assert all(x['category']=='kids' for x in json.loads(data)['movies'])
    status,_,op=req('POST','/api/auth/login',{'username':'operador','password':'op123'});assert status==200;op=op.split(';',1)[0]
    status,_,_=req('DELETE','/api/users/u-kids',cookie=op);assert status==403,status
    print('functional_smoke_ok')
finally:
    p.terminate();p.wait(timeout=5)
