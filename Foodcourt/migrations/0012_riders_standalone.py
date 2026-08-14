from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_riders(apps, schema_editor):
    Riders = apps.get_model('Foodcourt', 'Riders')
    RiderApplication = apps.get_model('Foodcourt', 'RiderApplication')
    User = apps.get_model('auth', 'User')

    for app in RiderApplication.objects.select_related('user').all():
        user = app.user
        rider = Riders(
            username=user.username or app.email,
            email=app.email or user.email,
            password=user.password,
            first_name=app.first_name,
            last_name=app.last_name,
            phone=app.phone,
            dob=app.dob,
            avatar=app.avatar,
            address=app.address,
            city=app.city,
            state=app.state,
            country=app.country,
            postal_code=app.postal_code,
            vehicle_type=app.vehicle_type,
            vehicle_brand=app.vehicle_brand,
            vehicle_model=app.vehicle_model,
            vehicle_color=app.vehicle_color,
            vehicle_plate=app.vehicle_plate,
            bank_name=app.bank_name,
            account_name=app.account_name,
            account_number=app.account_number,
            documents=app.documents,
            status=app.status,
            is_active=user.is_active,
        )
        rider.save()
        Riders.objects.filter(pk=rider.pk).update(created_at=app.created_at, updated_at=app.updated_at)


def reverse_migrate_riders(apps, schema_editor):
    Riders = apps.get_model('Foodcourt', 'Riders')
    Riders.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('Foodcourt', '0011_order_rider'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Riders',
        ),
        migrations.CreateModel(
            name='Riders',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=150, unique=True)),
                ('email', models.EmailField(max_length=500, unique=True)),
                ('password', models.CharField(max_length=128)),
                ('first_name', models.CharField(default='', max_length=200)),
                ('last_name', models.CharField(default='', max_length=200)),
                ('phone', models.CharField(default='', max_length=30)),
                ('gender', models.CharField(blank=True, default='', max_length=20)),
                ('dob', models.DateField(blank=True, null=True)),
                ('avatar', models.CharField(blank=True, default='', max_length=500)),
                ('address', models.TextField(default='')),
                ('city', models.CharField(default='', max_length=200)),
                ('state', models.CharField(default='', max_length=200)),
                ('country', models.CharField(default='', max_length=200)),
                ('postal_code', models.CharField(blank=True, default='', max_length=50)),
                ('vehicle_type', models.CharField(default='', max_length=100)),
                ('vehicle_brand', models.CharField(default='', max_length=200)),
                ('vehicle_model', models.CharField(default='', max_length=200)),
                ('vehicle_color', models.CharField(default='', max_length=100)),
                ('vehicle_plate', models.CharField(default='', max_length=100)),
                ('bank_name', models.CharField(default='', max_length=200)),
                ('account_name', models.CharField(default='', max_length=200)),
                ('account_number', models.CharField(default='', max_length=30)),
                ('documents', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('verified', 'Verified'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('is_active', models.BooleanField(default=False)),
                ('location', models.CharField(blank=True, default='', max_length=500)),
                ('payments', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'Riders',
                'ordering': ['-created_at'],
                'managed': True,
            },
        ),
        migrations.RunPython(migrate_riders, reverse_migrate_riders),
        migrations.DeleteModel(
            name='RiderApplication',
        ),
        migrations.AlterField(
            model_name='order',
            name='rider',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='delivery_orders', to='Foodcourt.riders'),
        ),
        migrations.AlterField(
            model_name='verificationcode',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verification_codes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='verificationcode',
            name='rider',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verification_codes', to='Foodcourt.riders'),
        ),
    ]
