from django.db import migrations


def fix_vendor_role(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='Vendor').update(role='VENDOR')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(
            fix_vendor_role,
            reverse_code=lambda apps, schema_editor: (
                apps.get_model('accounts', 'User')
                .objects.filter(role='VENDOR')
                .update(role='Vendor')
            ),
        ),
    ]