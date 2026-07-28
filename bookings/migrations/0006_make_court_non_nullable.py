from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0005_court_field_migration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='court',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='courts.court'),
        ),
    ]
