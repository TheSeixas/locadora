import importlib.util
import io
import time
import unittest
from pathlib import Path

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('server',root/'server.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class FakeHandler:
    def __init__(self,cookie=''):
        self.headers={'Cookie':cookie}

class RentalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m.seed()

    def tearDown(self):
        m.LOGIN_ATTEMPTS.clear()
        m.SESSIONS.clear()
        c=m._db()
        seed_ids=tuple(x[0] for x in m.SEED['users'])
        c.execute('DELETE FROM users WHERE id NOT IN (?,?,?,?)',seed_ids)
        for uid,u,pwd,age,active,is_kids,role in m.SEED['users']:
            c.execute('UPDATE users SET username=?,age=?,active=?,is_kids=?,role=? WHERE id=?',(u,age,active,is_kids,role,uid))
        c.commit();c.close()

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

    def test_session_revalidates_database_status(self):
        token='session-test'
        with m.LOCK:m.SESSIONS[token]={'user_id':'u-kids','created_at':time.time(),'expires_at':time.time()+60}
        self.assertEqual(m.auth_user(FakeHandler('bdk_session='+token))['id'],'u-kids')
        c=m._db();c.execute('UPDATE users SET active=0 WHERE id=?',('u-kids',));c.commit();c.close()
        self.assertIsNone(m.auth_user(FakeHandler('bdk_session='+token)))
        self.assertNotIn(token,m.SESSIONS)

    def test_expired_session_is_rejected(self):
        token='expired-test'
        with m.LOCK:m.SESSIONS[token]={'user_id':'u-admin','created_at':time.time()-100,'expires_at':time.time()-1}
        self.assertIsNone(m.auth_user(FakeHandler('bdk_session='+token)))

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

    def test_body_limit(self):
        class BodyHandler:
            headers={'Content-Length':str(m.MAX_BODY_BYTES+1)}
            rfile=io.BytesIO(b'{}')
        with self.assertRaises(ValueError) as e:m.Handler._json(BodyHandler())
        self.assertEqual(str(e.exception),'PAYLOAD_TOO_LARGE')

if __name__=='__main__':unittest.main(verbosity=2)
