import importlib.util
import io
import time
import unittest
import tempfile
import shutil
from pathlib import Path

root=Path(__file__).resolve().parents[1]
TEST_USERS=[('u-admin','admin','admin123',35,1,0,'ADMIN'),('u-op','operador','op123',28,1,0,'OPERATIONAL'),('u-kids','crianca','kids123',12,1,1,'CUSTOMER'),('u-inactive','inativo','inactive123',25,0,0,'CUSTOMER')]
spec=importlib.util.spec_from_file_location('server',root/'server.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class FakeHandler:
    def __init__(self,cookie=''):
        self.headers={'Cookie':cookie}

class RentalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir=tempfile.mkdtemp(prefix='locadora-fenix-tests-')
        m.DB=Path(cls.tempdir)/'test.sqlite3'
        m.seed()
        c=m._db()
        for uid,username,password,age,active,is_kids,role in TEST_USERS:
            c.execute('INSERT INTO users(id,username,password_hash,age,active,is_kids,role) VALUES(?,?,?,?,?,?,?)',(uid,username,m._hash(password),age,active,is_kids,role))
        c.commit();c.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir,ignore_errors=True)

    def tearDown(self):
        m.LOGIN_ATTEMPTS.clear();m.REGISTER_ATTEMPTS.clear();m.SESSIONS.clear()
        c=m._db()
        c.execute('DELETE FROM users')
        for uid,username,password,age,active,is_kids,role in TEST_USERS:
            c.execute('INSERT INTO users(id,username,password_hash,age,active,is_kids,role) VALUES(?,?,?,?,?,?,?)',(uid,username,m._hash(password),age,active,is_kids,role))
        c.commit();c.close()



    def test_production_bootstrap_requires_admin_secrets(self):
        original_db=m.DB
        original_host=m.HOST
        import os
        original_env={key:os.environ.get(key) for key in ('BOOTSTRAP_ADMIN_USERNAME','BOOTSTRAP_ADMIN_PASSWORD')}
        try:
            m.DB=Path(self.tempdir)/'missing-bootstrap.sqlite3'
            m.HOST='0.0.0.0'
            for key in original_env:os.environ.pop(key,None)
            with self.assertRaises(RuntimeError) as e:m.bootstrap_admin()
            self.assertEqual(str(e.exception),'BOOTSTRAP_ADMIN_CONFIGURATION_REQUIRED')
        finally:
            m.DB=original_db;m.HOST=original_host
            for key,value in original_env.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value

    def test_legacy_demo_cleanup_runs_only_once(self):
        # Use an isolated DB to prove that a real account named "admin" is not deleted on every restart.
        original_db=m.DB
        import os
        original_env={key:os.environ.get(key) for key in ('BOOTSTRAP_ADMIN_USERNAME','BOOTSTRAP_ADMIN_PASSWORD')}
        path=Path(self.tempdir)/'cleanup-once.sqlite3'
        try:
            m.DB=path
            for key in original_env:os.environ.pop(key,None)
            m.seed()
            c=m._db()
            c.execute('INSERT INTO users(id,username,password_hash,age,active,is_kids,role) VALUES(?,?,?,?,?,?,?)',('real-admin-name','admin',m._hash('CustomerPass123!'),30,1,0,'CUSTOMER'))
            c.commit();c.close()
            m.seed()
            c=m._db();row=c.execute("SELECT id FROM users WHERE username='admin'").fetchone();c.close()
            self.assertIsNotNone(row)
        finally:
            m.DB=original_db
            for key,value in original_env.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value

    def test_client_ip_uses_rightmost_valid_forwarded_address(self):
        from http.server import BaseHTTPRequestHandler
        h=object.__new__(m.Handler)
        h.headers={'X-Forwarded-For':'198.51.100.7, 203.0.113.9'}
        h.client_address=('127.0.0.1',12345)
        self.assertEqual(h._client_ip(),'203.0.113.9')

    def test_origin_validation_rejects_cross_origin_mutations(self):
        h=object.__new__(m.Handler)
        h.headers={'Origin':'https://attacker.example','Host':'locadora.example'}
        self.assertFalse(h._origin_allowed())
        h.headers={'Origin':'https://locadora.example','Host':'locadora.example'}
        self.assertTrue(h._origin_allowed())

    def test_unauthenticated_user_cannot_access_catalog(self):
        with self.assertRaises(PermissionError) as e:m.visible_movies(None)
        self.assertEqual(str(e.exception),'AUTH_REQUIRED')

    def test_inactive_user_cannot_access_catalog(self):
        with self.assertRaises(PermissionError) as e:m.visible_movies({'active':False,'age':25,'is_kids':False,'role':'CUSTOMER'})
        self.assertEqual(str(e.exception),'USER_INACTIVE')

    def test_kids_only_kids(self):
        ms=m.visible_movies({'active':True,'age':12,'is_kids':True,'role':'CUSTOMER'})
        self.assertEqual([x['category'] for x in ms],['kids'])

    def test_under18_no_adult(self):
        ms=m.visible_movies({'active':True,'age':17,'is_kids':False,'role':'CUSTOMER'})
        self.assertFalse(any(x['category']=='adult' for x in ms))

    def test_operational_cannot_delete_users(self):
        with self.assertRaises(PermissionError) as e:m.delete_user({'role':'OPERATIONAL','id':'u-op'},'u-kids')
        self.assertEqual(str(e.exception),'DELETE_FORBIDDEN')

    def test_admin_can_delete_customer(self):
        created=m.create_user({'role':'ADMIN','id':'u-admin'},{'username':'tempuser','password':'validpass123','age':25,'active':True})
        self.assertEqual(m.delete_user({'role':'ADMIN','id':'u-admin'},created['id'])['deleted'],created['id'])

    def test_operational_cannot_change_admin_status(self):
        with self.assertRaises(PermissionError) as e:m.set_active({'role':'OPERATIONAL','id':'u-op'},'u-admin',False)
        self.assertEqual(str(e.exception),'ADMIN_MANAGEMENT_FORBIDDEN')

    def test_admin_cannot_delete_admin(self):
        with self.assertRaises(PermissionError) as e:m.delete_user({'role':'ADMIN','id':'u-admin'},'u-admin')
        self.assertEqual(str(e.exception),'ADMIN_DELETE_FORBIDDEN')

    def test_user_cannot_deactivate_self(self):
        with self.assertRaises(PermissionError) as e:m.set_active({'role':'ADMIN','id':'u-admin'},'u-admin',False)
        self.assertEqual(str(e.exception),'SELF_DEACTIVATION_FORBIDDEN')

    def test_invalid_username_is_rejected(self):
        with self.assertRaises(ValueError) as e:m.validate_user_input({'username':'ab','password':'validpass123','age':18})
        self.assertEqual(str(e.exception),'INVALID_USERNAME')

    def test_invalid_password_is_rejected(self):
        with self.assertRaises(ValueError) as e:m.validate_user_input({'username':'validuser','password':'123','age':18})
        self.assertEqual(str(e.exception),'INVALID_PASSWORD')

    def test_invalid_age_is_rejected(self):
        for age in (-1,121,17.9,True,'18'):
            with self.subTest(age=age), self.assertRaises(ValueError) as e:m.validate_user_input({'username':'validnewuser','password':'validpass123','age':age})
            self.assertEqual(str(e.exception),'INVALID_AGE')

    def test_kids_flag_is_derived_from_age(self):
        self.assertTrue(m.validate_user_input({'username':'validnewuser','password':'validpass123','age':12,'is_kids':False})['is_kids'])
        self.assertFalse(m.validate_user_input({'username':'validnewuser','password':'validpass123','age':18,'is_kids':True})['is_kids'])

    def test_invalid_active_is_rejected(self):
        with self.assertRaises(ValueError) as e:m.validate_user_input({'username':'validnewuser','password':'validpass123','age':18,'active':'yes'})
        self.assertEqual(str(e.exception),'INVALID_ACTIVE')

    def test_valid_user_creation(self):
        u=m.create_user({'role':'ADMIN','id':'u-admin'},{'username':'validnewuser','password':'validpass123','age':12,'active':True})
        self.assertEqual(u['username'],'validnewuser')
        self.assertTrue(u['is_kids'])

    def test_admin_can_create_operational_user(self):
        u=m.create_user({'role':'ADMIN','id':'u-admin'},{'username':'newoperator','password':'validpass123','age':29,'active':True,'role':'OPERATIONAL'})
        self.assertEqual(u['role'],'OPERATIONAL')
        m.delete_user({'role':'ADMIN','id':'u-admin'},u['id'])

    def test_operational_cannot_create_operational_user(self):
        with self.assertRaises(PermissionError) as e:
            m.create_user({'role':'OPERATIONAL','id':'u-op'},{'username':'newoperator','password':'validpass123','age':29,'active':True,'role':'OPERATIONAL'})
        self.assertEqual(str(e.exception),'ROLE_ASSIGNMENT_FORBIDDEN')

    def test_admin_cannot_create_another_admin_from_user_form(self):
        with self.assertRaises(ValueError) as e:
            m.create_user({'role':'ADMIN','id':'u-admin'},{'username':'secondadmin','password':'validpass123','age':29,'active':True,'role':'ADMIN'})
        self.assertEqual(str(e.exception),'INVALID_ROLE')

    def test_admin_can_edit_customer_and_promote_to_operator(self):
        u=m.create_user({'role':'ADMIN','id':'u-admin'},{'username':'editableuser','password':'validpass123','age':24,'active':True})
        changed=m.update_user({'role':'ADMIN','id':'u-admin'},u['id'],{'username':'editeduser','age':12,'active':True,'role':'OPERATIONAL'})
        self.assertEqual(changed['username'],'editeduser')
        self.assertEqual(changed['role'],'OPERATIONAL')
        self.assertTrue(changed['is_kids'])
        m.delete_user({'role':'ADMIN','id':'u-admin'},u['id'])

    def test_admin_can_reset_non_admin_password(self):
        u=m.create_user({'role':'ADMIN','id':'u-admin'},{'username':'passworduser','password':'validpass123','age':24,'active':True})
        m.update_user({'role':'ADMIN','id':'u-admin'},u['id'],{'password':'changedpass123'})
        c=m._db();stored=c.execute('SELECT password_hash FROM users WHERE id=?',(u['id'],)).fetchone()['password_hash'];c.close()
        self.assertTrue(m._verify('changedpass123',stored))
        m.delete_user({'role':'ADMIN','id':'u-admin'},u['id'])

    def test_operational_can_edit_customer_but_not_change_role_or_password(self):
        u=m.create_user({'role':'ADMIN','id':'u-admin'},{'username':'operatorcanedit','password':'validpass123','age':24,'active':True})
        changed=m.update_user({'role':'OPERATIONAL','id':'u-op'},u['id'],{'username':'customerupdated','age':31,'active':True})
        self.assertEqual(changed['username'],'customerupdated')
        self.assertEqual(changed['role'],'CUSTOMER')
        with self.assertRaises(PermissionError) as e:
            m.update_user({'role':'OPERATIONAL','id':'u-op'},u['id'],{'role':'OPERATIONAL'})
        self.assertEqual(str(e.exception),'ROLE_ASSIGNMENT_FORBIDDEN')
        with self.assertRaises(PermissionError) as e:
            m.update_user({'role':'OPERATIONAL','id':'u-op'},u['id'],{'password':'changedpass123'})
        self.assertEqual(str(e.exception),'PASSWORD_RESET_FORBIDDEN')
        m.delete_user({'role':'ADMIN','id':'u-admin'},u['id'])

    def test_admin_accounts_cannot_be_edited_through_user_management(self):
        with self.assertRaises(PermissionError) as e:
            m.update_user({'role':'ADMIN','id':'u-admin'},'u-admin',{'username':'renamedadmin','age':36,'active':True,'role':'CUSTOMER'})
        self.assertEqual(str(e.exception),'ADMIN_MANAGEMENT_FORBIDDEN')

    def test_user_update_rejects_duplicate_username(self):
        u=m.create_user({'role':'ADMIN','id':'u-admin'},{'username':'editableunique','password':'validpass123','age':24,'active':True})
        with self.assertRaises(ValueError) as e:
            m.update_user({'role':'ADMIN','id':'u-admin'},u['id'],{'username':'operador','age':24,'active':True,'role':'CUSTOMER'})
        self.assertEqual(str(e.exception),'USERNAME_EXISTS')
        m.delete_user({'role':'ADMIN','id':'u-admin'},u['id'])

    def test_session_revalidates_database_status(self):
        token='session-test'
        with m.LOCK:m.SESSIONS[token]={'user_id':'u-kids','created_at':time.time(),'expires_at':time.time()+60}
        self.assertEqual(m.auth_user(FakeHandler('locadora_fenix_session='+token))['id'],'u-kids')
        c=m._db();c.execute('UPDATE users SET active=0 WHERE id=?',('u-kids',));c.commit();c.close()
        self.assertIsNone(m.auth_user(FakeHandler('locadora_fenix_session='+token)))
        self.assertNotIn(token,m.SESSIONS)

    def test_expired_session_is_rejected(self):
        token='expired-test'
        with m.LOCK:m.SESSIONS[token]={'user_id':'u-admin','created_at':time.time()-100,'expires_at':time.time()-1}
        self.assertIsNone(m.auth_user(FakeHandler('locadora_fenix_session='+token)))

    def test_login_rate_limit(self):
        key='rate-test'
        for _ in range(m.LOGIN_MAX_ATTEMPTS):
            with self.assertRaises(PermissionError):m.login('admin','wrong-password',key)
        with self.assertRaises(PermissionError) as e:m.login('admin','admin123',key)
        self.assertEqual(str(e.exception),'LOGIN_RATE_LIMITED')


    def test_non_admin_cannot_create_movie(self):
        with self.assertRaises(PermissionError) as e:m.create_movie({'role':'OPERATIONAL','id':'u-op'},{'title':'Novo','category':'action','year':2026,'rating':'14','description':'Descrição válida.'})
        self.assertEqual(str(e.exception),'CATALOG_ADMIN_ONLY')

    def test_admin_can_create_movie(self):
        movie=m.create_movie({'role':'ADMIN','id':'u-admin'},{'title':'Filme Novo','category':'action','year':2026,'rating':'14','description':'Descrição válida.'})
        self.assertTrue(movie['id'].startswith('m-'))
        self.assertEqual(movie['title'],'Filme Novo')
        m.delete_movie({'role':'ADMIN','id':'u-admin'},movie['id'])

    def test_admin_can_update_movie(self):
        movie=m.create_movie({'role':'ADMIN','id':'u-admin'},{'title':'Filme Editável','category':'action','year':2026,'rating':'14','description':'Antes.'})
        updated=m.update_movie({'role':'ADMIN','id':'u-admin'},movie['id'],{'title':'Filme Editado','category':'suspense','year':2025,'rating':'16','description':'Depois.'})
        self.assertEqual(updated['title'],'Filme Editado')
        self.assertEqual(updated['category'],'suspense')
        self.assertEqual(updated['rating'],'16')
        m.delete_movie({'role':'ADMIN','id':'u-admin'},movie['id'])

    def test_admin_can_delete_movie(self):
        movie=m.create_movie({'role':'ADMIN','id':'u-admin'},{'title':'Filme Removível','category':'horror','year':2026,'rating':'18','description':'Temporário.'})
        self.assertEqual(m.delete_movie({'role':'ADMIN','id':'u-admin'},movie['id'])['deleted'],movie['id'])

    def test_invalid_movie_title_is_rejected(self):
        with self.assertRaises(ValueError) as e:m.validate_movie_input({'title':'','category':'action','year':2026,'rating':'14','description':'válida'})
        self.assertEqual(str(e.exception),'INVALID_TITLE')

    def test_invalid_movie_category_is_rejected(self):
        with self.assertRaises(ValueError) as e:m.validate_movie_input({'title':'Novo','category':'nao-existe','year':2026,'rating':'14','description':'válida'})
        self.assertEqual(str(e.exception),'CATEGORY_NOT_FOUND')

    def test_invalid_movie_year_is_rejected(self):
        with self.assertRaises(ValueError) as e:m.validate_movie_input({'title':'Novo','category':'action','year':1800,'rating':'14','description':'válida'})
        self.assertEqual(str(e.exception),'INVALID_YEAR')

    def test_invalid_movie_rating_is_rejected(self):
        with self.assertRaises(ValueError) as e:m.validate_movie_input({'title':'Novo','category':'action','year':2026,'rating':'21','description':'válida'})
        self.assertEqual(str(e.exception),'INVALID_RATING')

    def test_missing_movie_is_rejected(self):
        with self.assertRaises(ValueError) as e:m.update_movie({'role':'ADMIN','id':'u-admin'},'m-nao-existe',{'title':'Novo','category':'action','year':2026,'rating':'14','description':'válida'})
        self.assertEqual(str(e.exception),'MOVIE_NOT_FOUND')

    def test_categories_are_available_to_authenticated_user(self):
        categories=m.list_categories({'role':'CUSTOMER','id':'u-kids'})
        self.assertTrue(any(c['slug']=='kids' for c in categories))


    def test_seed_does_not_overwrite_movie_changes(self):
        movie=m.create_movie({'role':'ADMIN','id':'u-admin'},{'title':'Persistente','category':'action','year':2026,'rating':'14','description':'Original.'})
        m.update_movie({'role':'ADMIN','id':'u-admin'},movie['id'],{'title':'Persistente Editado','category':'suspense','year':2025,'rating':'16','description':'Editado.'})
        m.seed()
        c=m._db();row=c.execute('SELECT title,category,year,rating,description FROM movies WHERE id=?',(movie['id'],)).fetchone();c.close()
        self.assertEqual(tuple(row),('Persistente Editado','suspense',2025,'16','Editado.'))
        m.delete_movie({'role':'ADMIN','id':'u-admin'},movie['id'])

    def test_seed_does_not_restore_deleted_seed_movie(self):
        m.delete_movie({'role':'ADMIN','id':'u-admin'},'m5')
        m.seed()
        c=m._db();row=c.execute('SELECT 1 FROM movies WHERE id=?',('m5',)).fetchone();c.close()
        self.assertIsNone(row)
        # restore the fixture for the remaining suite
        seed_movie=next(x for x in m.SEED['movies'] if x[0]=='m5')
        c=m._db();c.execute('INSERT INTO movies(id,title,category,year,rating,description) VALUES(?,?,?,?,?,?)',tuple(seed_movie));c.commit();c.close()

    def test_seed_removes_legacy_demo_accounts(self):
        old_db=m.DB
        isolated=Path(self.tempdir)/'legacy.sqlite3'
        m.DB=isolated
        try:
            c=m._db()
            c.execute("INSERT INTO users(id,username,password_hash,age,active,is_kids,role) VALUES(?,?,?,?,?,?,?)",('legacy-id','admin','salt:hash',35,1,0,'ADMIN'))
            c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('demo_seed_version','1')")
            c.commit();c.close()
            m.seed()
            c=m._db();rows=c.execute("SELECT username FROM users WHERE username IN ('admin','operador','crianca','inativo')").fetchall();c.close()
            self.assertEqual(rows,[])
        finally:
            m.DB=old_db
            isolated.unlink(missing_ok=True)

    def test_public_registration_forces_customer_role_and_active_status(self):
        u=m.register_customer({'username':'newcustomer','password':'longpassword123','age':17,'role':'ADMIN','active':False,'is_kids':True})
        self.assertEqual(u['role'],'CUSTOMER');self.assertTrue(u['active']);self.assertFalse(u['is_kids'])

    def test_public_registration_rejects_invalid_payload(self):
        with self.assertRaises(ValueError):m.register_customer({'username':'ab','password':'longpassword123','age':18})

    def test_bootstrap_admin_is_env_provisioned_and_not_reset(self):
        import os
        c=m._db();c.execute("DELETE FROM users WHERE role='ADMIN'");c.commit();c.close()
        old_u=os.environ.get('BOOTSTRAP_ADMIN_USERNAME');old_p=os.environ.get('BOOTSTRAP_ADMIN_PASSWORD')
        try:
            os.environ['BOOTSTRAP_ADMIN_USERNAME']='secureadmin';os.environ['BOOTSTRAP_ADMIN_PASSWORD']='VeryStrongLocalPass123!'
            self.assertTrue(m.bootstrap_admin());self.assertFalse(m.bootstrap_admin())
            c=m._db();row=c.execute("SELECT role FROM users WHERE username='secureadmin'").fetchone();c.close()
            self.assertEqual(row['role'],'ADMIN')
        finally:
            if old_u is None:os.environ.pop('BOOTSTRAP_ADMIN_USERNAME',None)
            else:os.environ['BOOTSTRAP_ADMIN_USERNAME']=old_u
            if old_p is None:os.environ.pop('BOOTSTRAP_ADMIN_PASSWORD',None)
            else:os.environ['BOOTSTRAP_ADMIN_PASSWORD']=old_p

    def test_body_limit(self):
        class BodyHandler:
            headers={'Content-Length':str(m.MAX_BODY_BYTES+1)}
            rfile=io.BytesIO(b'{}')
        with self.assertRaises(ValueError) as e:m.Handler._json(BodyHandler())
        self.assertEqual(str(e.exception),'PAYLOAD_TOO_LARGE')

if __name__=='__main__':unittest.main(verbosity=2)
