# Generated by Django 3.0b1 on 2019-11-14 09:21

from django.db import migrations

GROUP_NAME='teachers'

def apply_migration(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name=GROUP_NAME)

def reverse_migration(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get(name=GROUP_NAME).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_auto_20191113_1356'),
    ]

    operations = [
        migrations.RunPython(apply_migration, reverse_migration)
    ]