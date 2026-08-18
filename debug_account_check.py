import os
os.environ['DATABASE_URL'] = 'sqlite:///debug_account_check.db'
os.environ['SECRET_KEY'] = 'testsecret'
os.environ['CLOUDINARY_CLOUD_NAME'] = 'x'
os.environ['CLOUDINARY_API_KEY'] = 'x'
os.environ['CLOUDINARY_API_SECRET'] = 'x'
os.environ['FIREBASE_DATABASE_URL'] = 'https://example.firebaseio.com'

from ezticketapp import app, db
from ezticketapp.models import User, Role

with app.app_context():
    db.drop_all()
    db.create_all()
    admin = User(full_name='Admin', email='admin@test.com', password='hashed', role=Role.ADMIN, active=True)
    db.session.add(admin)
    db.session.commit()

    print('ROUTES:', [str(r) for r in app.url_map.iter_rules() if 'admin' in str(r)])

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        sess['_fresh'] = True

    resp = client.post('/admin/accounts/create', data={
        'full_name': 'Tester',
        'email': 'tester@example.com',
        'role': 'CUSTOMER',
        'status': 'active',
        'password': 'Abcdef1!'
    }, follow_redirects=False)

    print('STATUS:', resp.status_code)
    print('LOCATION:', resp.headers.get('Location'))
    print('COUNT:', User.query.count())
    print('USERS:', [(u.email, u.role.value, u.active) for u in User.query.all()])
