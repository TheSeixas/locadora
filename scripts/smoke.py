import http.client,json,os,socket,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
db_path=str(root/'data'/'smoke-test.sqlite3')
try:Path(db_path).unlink()
except FileNotFoundError:pass
p=subprocess.Popen([sys.executable,'server.py'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'PORT':str(port),'LOCADORA_DB_PATH':db_path,'BOOTSTRAP_ADMIN_USERNAME':'smokeadmin','BOOTSTRAP_ADMIN_PASSWORD':'SmokeTestStrongPass123!'})
def req(method,path,body=None,cookie=None):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);headers={'Content-Type':'application/json'}
    if cookie:headers['Cookie']=cookie
    c.request(method,path,body=json.dumps(body) if body is not None else None,headers=headers);r=c.getresponse();data=r.read();sc=r.getheader('Set-Cookie');c.close();return r.status,data,sc
try:
    html=(root/'public'/'index.html').read_text(encoding='utf-8');js=(root/'public'/'app.js').read_text(encoding='utf-8');css=(root/'public'/'styles.css').read_text(encoding='utf-8')
    assert 'loginForm' in html and '/app.js' in html and '/styles.css' in html
    assert 'Locadora Fênix' in html and 'BDK FACTORY' not in html and 'admin123' not in html
    assert 'registerForm' in html and 'userDialog' in html
    assert "if(!ageRaw||!Number.isInteger(age)||age<0||age>120)" in js and 'Informe uma idade válida em anos completos.' in js
    assert 'prompt(' not in js and 'alert(' not in js
    assert "addEventListener('submit'" in js and 'e.preventDefault()' in js and '/api/auth/login' in js
    assert '--accent:' in css and '.movie-grid' in css and '@media' in css and ':focus-visible' in css
    for _ in range(40):
        try: status,_,_=req('GET','/');assert status==200;break
        except Exception:time.sleep(.1)
    else:raise RuntimeError('SERVER_NOT_READY')
    for asset in ('/app.js','/styles.css'):status,_,_=req('GET',asset);assert status==200,f'{asset}:{status}'
    status,_,_=req('GET','/api/catalog');assert status==401,status
    # JSON-only API rejects simple cross-origin form content types.
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);c.request('POST','/api/auth/register',body=json.dumps({'username':'badcontent','password':'CustomerPass123!','age':18}),headers={'Content-Type':'text/plain','Origin':'https://attacker.example','Host':'127.0.0.1:'+str(port)});r=c.getresponse();r.read();assert r.status==403,r.status;c.close()
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);c.request('POST','/api/auth/register',body=json.dumps({'username':'badcontent','password':'CustomerPass123!','age':18}),headers={'Content-Type':'text/plain','Origin':'http://127.0.0.1:'+str(port),'Host':'127.0.0.1:'+str(port)});r=c.getresponse();r.read();assert r.status==415,r.status;c.close()
    status,_,sc=req('POST','/api/auth/login',{'username':'smokeadmin','password':'SmokeTestStrongPass123!'});assert status==200,status;cookie=sc.split(';',1)[0]
    status,data,_=req('GET','/api/catalog',cookie=cookie);assert status==200;payload=json.loads(data);assert len(payload['movies'])==5
    status,_,_=req('POST','/api/auth/login',{'username':'admin','password':'admin123'});assert status==401,status
    status,data,_=req('POST','/api/movies',{'title':'Smoke Movie','category':'action','year':2026,'rating':'14','description':'Filme temporário para teste.'},cookie);assert status==201,status;movie_id=json.loads(data)['movie']['id']
    status,data,_=req('PATCH','/api/movies/'+movie_id,{'title':'Smoke Movie Edited','category':'suspense','year':2025,'rating':'16','description':'Filme temporário editado.'},cookie);assert status==200 and json.loads(data)['movie']['title']=='Smoke Movie Edited',status
    status,data,_=req('DELETE','/api/movies/'+movie_id,cookie=cookie);assert status==200,status
    status,data,_=req('POST','/api/users',{'username':'smokeoperator','password':'OperatorPass123!','age':28,'active':True,'role':'OPERATIONAL'},cookie);assert status==201,status;operator=json.loads(data)['user'];assert operator['role']=='OPERATIONAL'
    status,data,_=req('POST','/api/users',{'username':'smokeeditable','password':'CustomerPass123!','age':24,'active':True,'role':'CUSTOMER'},cookie);assert status==201,status;editable=json.loads(data)['user']
    status,data,_=req('PATCH','/api/users/'+editable['id'],{'username':'smokeedited','age':12,'active':True,'role':'OPERATIONAL'},cookie);assert status==200,status;assert json.loads(data)['user']['role']=='OPERATIONAL' and json.loads(data)['user']['is_kids'] is True
    status,data,sc=req('POST','/api/auth/login',{'username':'smokeedited','password':'CustomerPass123!'});assert status==200,status;operator_cookie=sc.split(';',1)[0]
    status,_,_=req('POST','/api/users',{'username':'operatorcannotpromote','password':'CustomerPass123!','age':22,'active':True,'role':'OPERATIONAL'},operator_cookie);assert status==403,status
    status,data,_=req('POST','/api/users',{'username':'operatorcustomer','password':'CustomerPass123!','age':22,'active':True},operator_cookie);assert status==201,status;operator_customer=json.loads(data)['user'];assert operator_customer['role']=='CUSTOMER'
    status,_,_=req('PATCH','/api/users/'+operator_customer['id'],{'username':'operatorcustomer','age':22,'active':True,'role':'OPERATIONAL'},operator_cookie);assert status==403,status
    status,data,_=req('POST','/api/auth/register',{'username':'newcustomer','password':'CustomerPass123!','age':16,'role':'ADMIN','active':False});assert status==201,status
    customer=json.loads(data)['user'];assert customer['role']=='CUSTOMER' and customer['active'] is True
    status,_,_=req('POST','/api/auth/register',{'username':'newcustomer','password':'CustomerPass123!','age':16});assert status==409,status
    status,_,sc=req('POST','/api/auth/login',{'username':'newcustomer','password':'CustomerPass123!'});assert status==200,status;customer_cookie=sc.split(';',1)[0]
    status,data,_=req('GET','/api/catalog',cookie=customer_cookie);assert status==200,status;customer_catalog=json.loads(data);assert all(m['category']!='adult' for m in customer_catalog['movies'])
    status,_,_=req('POST','/api/movies',{'title':'Forbidden Movie','category':'action','year':2026,'rating':'14','description':'Cliente não deve cadastrar.'},customer_cookie);assert status==403,status
    status,_,_=req('POST','/api/auth/logout',cookie=customer_cookie);assert status==200,status
    status,_,_=req('GET','/api/catalog',cookie=customer_cookie);assert status==401,status
    print('functional_smoke_ok: bootstrap login, catalog CRUD, admin creates OPERATIONAL, admin edits/promotes user, operator role escalation denied, operator creates CUSTOMER, public registration, forced CUSTOMER role, duplicate protection, age filter, customer write denied, logout revokes session')
finally:
    p.terminate();p.wait(timeout=5)
    try:Path(db_path).unlink()
    except FileNotFoundError:pass
