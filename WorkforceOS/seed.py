import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenants.models import Tenant

User = get_user_model()

try:
    tenant, created = Tenant.objects.get_or_create(
        slug='demo',
        defaults={'name': 'Demo Company', 'plan': 'enterprise'}
    )
    if not User.objects.filter(email='admin@connecthr.com').exists():
        user = User.objects.create_user(
            email='admin@connecthr.com',
            password='Password123!',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True,
            tenant=tenant
        )
        print('Superuser created successfully: admin@connecthr.com / Password123!')
    else:
        user = User.objects.get(email='admin@connecthr.com')
        user.set_password('Password123!')
        user.tenant = tenant
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print('Superuser updated successfully: admin@connecthr.com / Password123!')
except Exception as e:
    import traceback
    traceback.print_exc()
