from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='address',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AddField(
            model_name='vendor',
            name='institution_number',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]