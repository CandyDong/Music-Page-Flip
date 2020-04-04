# Generated by Django 2.1.5 on 2020-04-03 22:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pageFlipper', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='scores',
        ),
        migrations.AddField(
            model_name='score',
            name='user_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='pageFlipper.Profile'),
        ),
    ]
