# Generated by Django 2.1.5 on 2020-04-18 18:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pageFlipper', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlipSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.IntegerField(blank=True, null=True)),
                ('score_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.RemoveField(
            model_name='profile',
            name='scores',
        ),
        migrations.AddField(
            model_name='rpi',
            name='macAddr',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='rpi',
            name='name',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='score',
            name='path',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='score',
            name='user_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='pageFlipper.Profile'),
        ),
        migrations.AddField(
            model_name='flipsession',
            name='user_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pageFlipper.Profile'),
        ),
    ]
