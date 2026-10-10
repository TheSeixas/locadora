import hashlib,hmac,json,os,secrets,sqlite3,threading,time,re,ipaddress
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
DB=Path(os.getenv('LOCADORA_DB_PATH', str(ROOT/'data'/'locadora.sqlite3')))
PUBLIC=ROOT/'public'
HOST=os.getenv('HOST','127.0.0.1')
PORT=int(os.getenv('PORT','3000'))
MAX_BODY_BYTES=int(os.getenv('MAX_BODY_BYTES','65536'))
SESSION_TTL_SECONDS=int(os.getenv('SESSION_TTL_SECONDS','28800'))
COOKIE_SECURE=os.getenv('COOKIE_SECURE','0').lower() in ('1','true','yes')
LOGIN_WINDOW_SECONDS=int(os.getenv('LOGIN_WINDOW_SECONDS','300'))
LOGIN_MAX_ATTEMPTS=int(os.getenv('LOGIN_MAX_ATTEMPTS','10'))
SESSIONS={}
LOGIN_ATTEMPTS={}
REGISTER_ATTEMPTS={}
LOCK=threading.Lock()
DEMO_USER_IDS=('u-admin','u-op','u-kids','u-inactive')
DEMO_USERNAMES=('admin','operador','crianca','inativo')
SEED={"categories":[["kids","Kids"],["action","Ação"],["suspense","Suspense"],["horror","Terror"],["adult","Adulto"]],"movies":[["m1","Aventuras do Robô","kids",2025,"L","Aventura leve para toda a família."],["m2","Detetive da Meia-Noite","suspense",2024,"14","Mistério e investigação."],["m3","Cidade em Chamas","action",2023,"16","Ação e perseguição."],["m4","Casa Sombria","horror",2022,"18","Terror psicológico."],["m5","Conteúdo Adulto Exemplo","adult",2024,"18","Conteúdo restrito a maiores de 18."]]}

USERNAME_RE=re.compile(r'^[A-Za-z0-9_.-]{3,30}$')
VALID_ROLES={'ADMIN','OPERATIONAL','CUSTOMER'}
VALID_RATINGS={'L','10','12','14','16','18'}
MOVIE_TITLE_MAX=100
MOVIE_DESCRIPTION_MAX=500
MOVIE_YEAR_MIN=1888
MOVIE_YEAR_MAX=2100

def _db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB,timeout=10)
    c.execute('PRAGMA busy_timeout=10000')
    c.row_factory=sqlite3.Row
    c.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT NOT NULL,age INTEGER NOT NULL,active INTEGER NOT NULL,is_kids INTEGER NOT NULL,role TEXT NOT NULL);CREATE TABLE IF NOT EXISTS categories(slug TEXT PRIMARY KEY,name TEXT NOT NULL);CREATE TABLE IF NOT EXISTS movies(id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,year INTEGER NOT NULL,rating TEXT NOT NULL,description TEXT NOT NULL);CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
    return c

def _hash(p,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),180000).hex()

def _verify(p,stored):
    try:
        salt,digest=stored.split(':',1)
        got=hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),180000).hex()
        return hmac.compare_digest(got,digest)
    except Exception:
        return False

def seed():
    """Initialize catalog once and migrate legacy demo accounts only once."""
    c=_db()
    cleanup=c.execute("SELECT value FROM app_meta WHERE key='legacy_demo_cleanup_version'").fetchone()
    if not cleanup:
        c.execute("DELETE FROM users WHERE id IN (?,?,?,?) OR username IN (?,?,?,?)",(*DEMO_USER_IDS,*DEMO_USERNAMES))
        c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('legacy_demo_cleanup_version','1')")
    initialized=c.execute("SELECT value FROM app_meta WHERE key='catalog_seed_version'").fetchone()
    if not initialized:
        for slug,name in SEED['categories']:
            c.execute('INSERT OR IGNORE INTO categories(slug,name) VALUES(?,?)',(slug,name))
        for movie in SEED['movies']:
            c.execute('INSERT OR IGNORE INTO movies(id,title,category,year,rating,description) VALUES(?,?,?,?,?,?)',tuple(movie))
        c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('catalog_seed_version','2')")
    c.commit();c.close()
    bootstrap_admin()

def bootstrap_admin():
    """Create the first admin only from deployment-provided environment secrets."""
    username=os.getenv('BOOTSTRAP_ADMIN_USERNAME','').strip()
    password=os.getenv('BOOTSTRAP_ADMIN_PASSWORD','')
    c=_db()
    exists=c.execute("SELECT 1 FROM users WHERE role='ADMIN' LIMIT 1").fetchone()
    if exists:
        c.close();return False
    if not username or not password:
        c.close()
        if HOST in ('0.0.0.0','::'):
            raise RuntimeError('BOOTSTRAP_ADMIN_CONFIGURATION_REQUIRED')
        return False
    if not USERNAME_RE.fullmatch(username) or not 12 <= len(password) <= 128:
        c.close();raise RuntimeError('BOOTSTRAP_ADMIN_CONFIGURATION_INVALID: username must be 3-30 allowed characters and password must be 12-128 characters')
    uid='u-'+secrets.token_hex(8)
    try:
        c.execute('INSERT INTO users(id,username,password_hash,age,active,is_kids,role) VALUES(?,?,?,?,?,?,?)',(uid,username,_hash(password),18,1,0,'ADMIN'))
        c.commit()
    except sqlite3.IntegrityError:
        c.close();raise RuntimeError('BOOTSTRAP_ADMIN_USERNAME_CONFLICT')
    c.close();return True

def row_user(r):
    return {'id':r['id'],'username':r['username'],'age':r['age'],'active':bool(r['active']),'is_kids':bool(r['is_kids']),'role':r['role']}

def validate_user_input(data):
    if not isinstance(data,dict):
        raise ValueError('INVALID_PAYLOAD')
    username=str(data.get('username','')).strip()
    password=str(data.get('password',''))
    age=data.get('age')
    if not USERNAME_RE.fullmatch(username):
        raise ValueError('INVALID_USERNAME')
    if not isinstance(age,int) or isinstance(age,bool) or not 0 <= age <= 120:
        raise ValueError('INVALID_AGE')
    if not 8 <= len(password) <= 128:
        raise ValueError('INVALID_PASSWORD')
    active=data.get('active',True)
    if not isinstance(active,bool):
        raise ValueError('INVALID_ACTIVE')
    return {'username':username,'password':password,'age':age,'active':active,'is_kids':age<13}

def auth_user(handler):
    cookie=handler.headers.get('Cookie','')
    token=cookie.split('locadora_fenix_session=',1)[-1].split(';',1)[0] if 'locadora_fenix_session=' in cookie else ''
    if not token:
        return None
    with LOCK:
        entry=SESSIONS.get(token)
        if not entry:
            return None
        if entry['expires_at'] <= time.time():
            SESSIONS.pop(token,None)
            return None
        uid=entry['user_id']
    c=_db();r=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone();c.close()
    if not r or not r['active']:
        with LOCK:SESSIONS.pop(token,None)
        return None
    return row_user(r)

def visible_movies(user):
    if not user: raise PermissionError('AUTH_REQUIRED')
    if not user['active']: raise PermissionError('USER_INACTIVE')
    c=_db();rows=c.execute('SELECT id,title,category,year,rating,description FROM movies ORDER BY id').fetchall();c.close()
    movies=[dict(r) for r in rows]
    if user['is_kids']: return [m for m in movies if m['category']=='kids']
    if user['age']<18: return [m for m in movies if m['category']!='adult']
    return movies

def _login_allowed(key):
    now=time.time()
    with LOCK:
        attempts=[t for t in LOGIN_ATTEMPTS.get(key,[]) if now-t < LOGIN_WINDOW_SECONDS]
        LOGIN_ATTEMPTS[key]=attempts
        return len(attempts) < LOGIN_MAX_ATTEMPTS

def _record_login_failure(key):
    with LOCK:
        LOGIN_ATTEMPTS.setdefault(key,[]).append(time.time())

def _clear_login_failures(key):
    with LOCK:LOGIN_ATTEMPTS.pop(key,None)

def login(username,password,rate_key='local'):
    if not _login_allowed(rate_key): raise PermissionError('LOGIN_RATE_LIMITED')
    c=_db();r=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone();c.close()
    if not r or not _verify(password,r['password_hash']):
        _record_login_failure(rate_key);raise PermissionError('INVALID_CREDENTIALS')
    u=row_user(r)
    if not u['active']: raise PermissionError('USER_INACTIVE')
    _clear_login_failures(rate_key)
    return u

def users(user):
    if not user or user['role'] not in ('ADMIN','OPERATIONAL'): raise PermissionError('FORBIDDEN')
    c=_db();rows=[row_user(r) for r in c.execute('SELECT * FROM users ORDER BY username')];c.close();return rows

def create_user(user,data):
    if not user or user['role'] not in ('ADMIN','OPERATIONAL'): raise PermissionError('FORBIDDEN')
    clean=validate_user_input(data)
    role=data.get('role','CUSTOMER')
    if role not in ('CUSTOMER','OPERATIONAL'):
        raise ValueError('INVALID_ROLE')
    if user['role']!='ADMIN' and role!='CUSTOMER':
        raise PermissionError('ROLE_ASSIGNMENT_FORBIDDEN')
    c=_db();uid='u-'+secrets.token_hex(6)
    try:
        c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',(uid,clean['username'],_hash(clean['password']),clean['age'],1 if clean['active'] else 0,1 if clean['is_kids'] else 0,role));c.commit()
    except sqlite3.IntegrityError:
        c.close();raise ValueError('USERNAME_EXISTS')
    r=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone();c.close();return row_user(r)

def update_user(user,uid,data):
    """Update a non-admin account while enforcing role boundaries on the server."""
    if not user or user['role'] not in ('ADMIN','OPERATIONAL'):
        raise PermissionError('FORBIDDEN')
    if not isinstance(data,dict):
        raise ValueError('INVALID_PAYLOAD')
    c=_db();current=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    if not current:
        c.close();raise ValueError('USER_NOT_FOUND')
    if current['role']=='ADMIN':
        c.close();raise PermissionError('ADMIN_MANAGEMENT_FORBIDDEN')
    if user['role']=='OPERATIONAL' and current['role']!='CUSTOMER':
        c.close();raise PermissionError('ADMIN_MANAGEMENT_FORBIDDEN')

    username=str(data.get('username',current['username'])).strip()
    age=data.get('age',current['age'])
    active=data.get('active',bool(current['active']))
    role=data.get('role',current['role'])
    password=str(data.get('password',''))
    if not USERNAME_RE.fullmatch(username):
        c.close();raise ValueError('INVALID_USERNAME')
    if not isinstance(age,int) or isinstance(age,bool) or not 0<=age<=120:
        c.close();raise ValueError('INVALID_AGE')
    if not isinstance(active,bool):
        c.close();raise ValueError('INVALID_ACTIVE')
    if role not in ('CUSTOMER','OPERATIONAL'):
        c.close();raise ValueError('INVALID_ROLE')
    if user['role']!='ADMIN' and role!=current['role']:
        c.close();raise PermissionError('ROLE_ASSIGNMENT_FORBIDDEN')
    if password and not 8<=len(password)<=128:
        c.close();raise ValueError('INVALID_PASSWORD')
    if password and user['role']!='ADMIN':
        c.close();raise PermissionError('PASSWORD_RESET_FORBIDDEN')
    if user['id']==uid and not active:
        c.close();raise PermissionError('SELF_DEACTIVATION_FORBIDDEN')
    try:
        if password:
            c.execute('UPDATE users SET username=?,age=?,is_kids=?,active=?,role=?,password_hash=? WHERE id=?',
                      (username,age,1 if age<13 else 0,1 if active else 0,role,_hash(password),uid))
        else:
            c.execute('UPDATE users SET username=?,age=?,is_kids=?,active=?,role=? WHERE id=?',
                      (username,age,1 if age<13 else 0,1 if active else 0,role,uid))
        c.commit()
    except sqlite3.IntegrityError:
        c.close();raise ValueError('USERNAME_EXISTS')
    result=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone();c.close();return row_user(result)

def register_customer(data):
    clean=validate_user_input({**data,'active':True})
    c=_db();uid='u-'+secrets.token_hex(8)
    try:
        c.execute('INSERT INTO users(id,username,password_hash,age,active,is_kids,role) VALUES(?,?,?,?,?,?,?)',(uid,clean['username'],_hash(clean['password']),clean['age'],1,1 if clean['is_kids'] else 0,'CUSTOMER'))
        c.commit();r=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    except sqlite3.IntegrityError:
        c.close();raise ValueError('USERNAME_EXISTS')
    c.close();return row_user(r)

def _registration_allowed(key):
    now=time.time()
    with LOCK:
        attempts=[t for t in REGISTER_ATTEMPTS.get(key,[]) if now-t < 3600]
        REGISTER_ATTEMPTS[key]=attempts
        if len(attempts)>=5:return False
        attempts.append(now);REGISTER_ATTEMPTS[key]=attempts
        return True

def set_active(user,uid,active):
    if not user or user['role'] not in ('ADMIN','OPERATIONAL'): raise PermissionError('FORBIDDEN')
    if not isinstance(active,bool): raise ValueError('INVALID_ACTIVE')
    c=_db();r=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    if not r: c.close();raise ValueError('USER_NOT_FOUND')
    if user['id']==uid and not active: c.close();raise PermissionError('SELF_DEACTIVATION_FORBIDDEN')
    if r['role']=='ADMIN': c.close();raise PermissionError('ADMIN_MANAGEMENT_FORBIDDEN')
    if user['role']=='OPERATIONAL' and r['role']!='CUSTOMER': c.close();raise PermissionError('ADMIN_MANAGEMENT_FORBIDDEN')
    c.execute('UPDATE users SET active=? WHERE id=?',(1 if active else 0,uid));c.commit();r=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone();c.close();return row_user(r)

def delete_user(user,uid):
    if not user or user['role']!='ADMIN': raise PermissionError('DELETE_FORBIDDEN')
    c=_db();r=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    if not r: c.close();raise ValueError('USER_NOT_FOUND')
    if r['role']=='ADMIN': c.close();raise PermissionError('ADMIN_DELETE_FORBIDDEN')
    c.execute('DELETE FROM users WHERE id=?',(uid,));c.commit();c.close();return {'deleted':uid}

def _category_exists(category):
    c=_db();row=c.execute('SELECT 1 FROM categories WHERE slug=?',(category,)).fetchone();c.close();return bool(row)

def validate_movie_input(data):
    if not isinstance(data,dict): raise ValueError('INVALID_PAYLOAD')
    title=str(data.get('title','')).strip()
    category=str(data.get('category','')).strip()
    description=str(data.get('description','')).strip()
    year=data.get('year')
    rating=str(data.get('rating','')).strip().upper()
    if not title or len(title)>MOVIE_TITLE_MAX: raise ValueError('INVALID_TITLE')
    if not USERNAME_RE.fullmatch(category): raise ValueError('INVALID_CATEGORY')
    if not _category_exists(category): raise ValueError('CATEGORY_NOT_FOUND')
    if not isinstance(year,int) or isinstance(year,bool) or not MOVIE_YEAR_MIN<=year<=MOVIE_YEAR_MAX: raise ValueError('INVALID_YEAR')
    if rating not in VALID_RATINGS: raise ValueError('INVALID_RATING')
    if not description or len(description)>MOVIE_DESCRIPTION_MAX: raise ValueError('INVALID_DESCRIPTION')
    return {'title':title,'category':category,'year':year,'rating':rating,'description':description}

def list_categories(user):
    if not user: raise PermissionError('AUTH_REQUIRED')
    c=_db();rows=[dict(r) for r in c.execute('SELECT slug,name FROM categories ORDER BY name')];c.close();return rows

def list_movies(user):
    return visible_movies(user)

def create_movie(user,data):
    if not user or user['role']!='ADMIN': raise PermissionError('CATALOG_ADMIN_ONLY')
    clean=validate_movie_input(data)
    c=_db();movie_id='m-'+secrets.token_hex(6)
    c.execute('INSERT INTO movies(id,title,category,year,rating,description) VALUES(?,?,?,?,?,?)',(movie_id,clean['title'],clean['category'],clean['year'],clean['rating'],clean['description']))
    c.commit();r=c.execute('SELECT id,title,category,year,rating,description FROM movies WHERE id=?',(movie_id,)).fetchone();c.close();return dict(r)

def update_movie(user,movie_id,data):
    if not user or user['role']!='ADMIN': raise PermissionError('CATALOG_ADMIN_ONLY')
    clean=validate_movie_input(data)
    c=_db();r=c.execute('SELECT id FROM movies WHERE id=?',(movie_id,)).fetchone()
    if not r: c.close();raise ValueError('MOVIE_NOT_FOUND')
    c.execute('UPDATE movies SET title=?,category=?,year=?,rating=?,description=? WHERE id=?',(clean['title'],clean['category'],clean['year'],clean['rating'],clean['description'],movie_id))
    c.commit();r=c.execute('SELECT id,title,category,year,rating,description FROM movies WHERE id=?',(movie_id,)).fetchone();c.close();return dict(r)

def delete_movie(user,movie_id):
    if not user or user['role']!='ADMIN': raise PermissionError('CATALOG_ADMIN_ONLY')
    c=_db();r=c.execute('SELECT id FROM movies WHERE id=?',(movie_id,)).fetchone()
    if not r: c.close();raise ValueError('MOVIE_NOT_FOUND')
    c.execute('DELETE FROM movies WHERE id=?',(movie_id,));c.commit();c.close();return {'deleted':movie_id}

class Handler(BaseHTTPRequestHandler):
    server_version='LocadoraFenix/1.0';protocol_version='HTTP/1.0'
    def _send(self,status,payload=None,ctype='application/json',cookies=None):
        data=b'' if payload is None else(payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False).encode())
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");self.send_header('Content-Length',str(len(data)));self.send_header('Connection','close')
        if cookies:
            for x in cookies:self.send_header('Set-Cookie',x)
        self.end_headers();self.close_connection=True
        if data:self.wfile.write(data);self.wfile.flush()
    def _json(self):
        try:n=int(self.headers.get('Content-Length','0') or 0)
        except ValueError:raise ValueError('INVALID_CONTENT_LENGTH')
        if n > MAX_BODY_BYTES: raise ValueError('PAYLOAD_TOO_LARGE')
        content_type=self.headers.get('Content-Type','').split(';',1)[0].strip().lower()
        if content_type!='application/json':raise ValueError('JSON_CONTENT_TYPE_REQUIRED')
        raw=self.rfile.read(n) if n else b'{}'
        try:return json.loads(raw or b'{}')
        except json.JSONDecodeError:raise ValueError('INVALID_JSON')

    def _client_ip(self):
        """Use the rightmost proxy-appended XFF address when present (Render edge), else socket peer."""
        forwarded=self.headers.get('X-Forwarded-For','')
        if forwarded:
            candidate=forwarded.split(',')[-1].strip()
            try:return str(ipaddress.ip_address(candidate))
            except ValueError:pass
        return self.client_address[0]

    def _origin_allowed(self):
        origin=self.headers.get('Origin')
        if not origin:return True
        try:
            parsed=urlsplit(origin)
            return parsed.scheme in ('http','https') and parsed.netloc.lower()==self.headers.get('Host','').lower()
        except ValueError:
            return False
    def _session_cookie(self,token,max_age=None):
        secure='; Secure' if COOKIE_SECURE else ''
        age=f'; Max-Age={max_age}' if max_age is not None else ''
        return f'locadora_fenix_session={token}; HttpOnly; SameSite=Lax; Path=/{age}{secure}'
    def _api(self):
        try:
            if self.command in ('POST','PATCH','DELETE') and not self._origin_allowed():
                return self._send(403,{'error':'ORIGIN_NOT_ALLOWED'})
            if self.command=='POST' and self.path=='/api/auth/register':
                payload=self._json()
                if not isinstance(payload,dict):raise ValueError('INVALID_PAYLOAD')
                if not _registration_allowed(self._client_ip()):raise PermissionError('REGISTRATION_RATE_LIMITED')
                customer=register_customer(payload)
                return self._send(201,{'user':customer})
            if self.command=='POST' and self.path=='/api/auth/login':
                payload=self._json()
                if not isinstance(payload,dict):raise ValueError('INVALID_PAYLOAD')
                u=login(str(payload.get('username','')).strip(),str(payload.get('password','')),self._client_ip()+'|'+str(payload.get('username','')).strip().lower());t=secrets.token_urlsafe(32)
                with LOCK:SESSIONS[t]={'user_id':u['id'],'created_at':time.time(),'expires_at':time.time()+SESSION_TTL_SECONDS}
                return self._send(200,{'user':u},cookies=[self._session_cookie(t,SESSION_TTL_SECONDS)])
            if self.command=='POST' and self.path=='/api/auth/logout':
                cookie=self.headers.get('Cookie','');token=cookie.split('locadora_fenix_session=',1)[-1].split(';',1)[0] if 'locadora_fenix_session=' in cookie else ''
                with LOCK:SESSIONS.pop(token,None)
                return self._send(200,{'ok':True},cookies=[self._session_cookie('',0)])
            if self.command=='GET' and self.path=='/health':return self._send(200,{'status':'ok'})
            u=auth_user(self)
            if self.command=='GET' and self.path=='/api/catalog':return self._send(200,{'user':u,'movies':visible_movies(u),'categories':list_categories(u)})
            if self.command=='GET' and self.path=='/api/users':return self._send(200,{'users':users(u)})
            if self.command=='POST' and self.path=='/api/users':return self._send(201,{'user':create_user(u,self._json())})
            if self.command=='POST' and self.path=='/api/movies':return self._send(201,{'movie':create_movie(u,self._json())})
            if self.path.startswith('/api/movies/') and self.command=='PATCH':return self._send(200,{'movie':update_movie(u,self.path.rsplit('/',1)[-1],self._json())})
            if self.path.startswith('/api/movies/') and self.command=='DELETE':return self._send(200,delete_movie(u,self.path.rsplit('/',1)[-1]))
            if self.path.startswith('/api/users/') and self.command=='PATCH':
                payload=self._json()
                if isinstance(payload,dict) and set(payload.keys())=={'active'}:
                    updated=set_active(u,self.path.rsplit('/',1)[-1],payload.get('active'))
                else:
                    updated=update_user(u,self.path.rsplit('/',1)[-1],payload)
                return self._send(200,{'user':updated})
            if self.path.startswith('/api/users/') and self.command=='DELETE':return self._send(200,delete_user(u,self.path.rsplit('/',1)[-1]))
            return self._send(404,{'error':'NOT_FOUND'})
        except PermissionError as e:
            code={'AUTH_REQUIRED':401,'USER_INACTIVE':403,'FORBIDDEN':403,'DELETE_FORBIDDEN':403,'ADMIN_DELETE_FORBIDDEN':403,'ADMIN_MANAGEMENT_FORBIDDEN':403,'ROLE_ASSIGNMENT_FORBIDDEN':403,'PASSWORD_RESET_FORBIDDEN':403,'SELF_DEACTIVATION_FORBIDDEN':403,'INVALID_CREDENTIALS':401,'LOGIN_RATE_LIMITED':429,'REGISTRATION_RATE_LIMITED':429,'CATALOG_ADMIN_ONLY':403}.get(str(e),403);return self._send(code,{'error':str(e)})
        except ValueError as e:
            code=413 if str(e)=='PAYLOAD_TOO_LARGE' else 415 if str(e)=='JSON_CONTENT_TYPE_REQUIRED' else 409 if str(e)=='USERNAME_EXISTS' else 404 if str(e) in ('MOVIE_NOT_FOUND','USER_NOT_FOUND') else 400
            return self._send(code,{'error':str(e)})
        except Exception:
            return self._send(500,{'error':'INTERNAL_ERROR'})
    def do_GET(self):
        if self.path.startswith('/api/') or self.path=='/health':return self._api()
        pathname=self.path.split('?',1)[0];relp='index.html' if pathname=='/' else pathname.lstrip('/')
        if relp.startswith('..') or relp.startswith('/'):return self._send(403,b'forbidden','text/plain')
        target=(PUBLIC/relp).resolve()
        if not target.is_relative_to(PUBLIC.resolve()) or not target.is_file():return self._send(404,{'error':'NOT_FOUND'})
        ctype='text/html; charset=utf-8' if target.suffix=='.html' else 'text/css; charset=utf-8' if target.suffix=='.css' else 'application/javascript; charset=utf-8' if target.suffix=='.js' else 'application/octet-stream'
        return self._send(200,target.read_bytes(),ctype=ctype)
    def do_POST(self):return self._api() if self.path.startswith('/api/') else self._send(404,{'error':'NOT_FOUND'})
    def do_PATCH(self):return self._api()
    def do_DELETE(self):return self._api()
    def log_message(self,format,*args):return

if __name__=='__main__':
    seed();print(f'Locadora Fênix listening on {HOST}:{PORT}');server=ThreadingHTTPServer((HOST,PORT),Handler);server.allow_reuse_address=True;server.serve_forever()
