import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_fields_to_courts(apps, schema_editor):
    try:
        Court = apps.get_model('courts', 'Court')
        CourtSchedule = apps.get_model('courts', 'CourtSchedule')
        CourtBlock = apps.get_model('courts', 'CourtBlock')
        Field = apps.get_model('fields', 'Field')
        Booking = apps.get_model('bookings', 'Booking')
    except LookupError:
        return

    try:
        FieldSchedule = apps.get_model('fields', 'FieldSchedule')
    except LookupError:
        FieldSchedule = None

    try:
        FieldBlock = apps.get_model('fields', 'FieldBlock')
    except LookupError:
        FieldBlock = None

    field_map = {}
    for field in Field.objects.all():
        court = Court.objects.create(
            name=field.name,
            sport_type='FOOTBALL',
            surface=field.surface or 'SYNTHETIC',
            players_per_side=field.field_type,
            price_per_hour=field.price_per_hour,
            is_active=field.is_active,
            description=field.description or '',
            deleted_at=field.deleted_at,
        )
        field_map[field.id] = court.id

    if FieldSchedule:
        for schedule in FieldSchedule.objects.all():
            court_id = field_map.get(schedule.field_id)
            if court_id:
                CourtSchedule.objects.create(
                    court_id=court_id,
                    day_of_week=schedule.day_of_week,
                    open_time=schedule.open_time,
                    close_time=schedule.close_time,
                    is_active=schedule.is_active,
                )

    if FieldBlock:
        for block in FieldBlock.objects.all():
            court_id = field_map.get(block.field_id)
            if court_id:
                CourtBlock.objects.create(
                    court_id=court_id,
                    date=block.date,
                    start_time=block.start_time,
                    end_time=block.end_time,
                    reason=block.reason or '',
                    created_by=block.created_by,
                )

    for booking in Booking.objects.all():
        court_id = field_map.get(booking.field_id)
        if court_id:
            booking.court_id = court_id
            booking.save(update_fields=['court_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_default_total_price'),
        ('courts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='commission',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name='booking',
            name='court',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='courts.court'),
        ),
        migrations.RunPython(migrate_fields_to_courts, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name='booking',
            name='bookings_bo_field_i_de5fc7_idx',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='field',
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['court', 'date'], name='bookings_bo_court_i_ca21c0_idx'),
        ),
    ]
