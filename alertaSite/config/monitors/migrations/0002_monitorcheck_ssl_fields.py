# Generated migration for new feature fields

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('monitors', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='monitor',
            name='response_time_ms',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='monitor',
            name='ssl_days_left',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='monitor',
            name='ssl_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='monitor',
            name='ssl_last_checked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='monitor',
            name='ssl_status',
            field=models.CharField(default='unknown', max_length=20),
        ),
        migrations.CreateModel(
            name='MonitorCheck',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('up', 'Up'), ('down', 'Down')], max_length=10)),
                ('response_time_ms', models.IntegerField(blank=True, null=True)),
                ('reason', models.TextField(blank=True, default='')),
                ('checked_at', models.DateTimeField(auto_now_add=True)),
                ('monitor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checks', to='monitors.monitor')),
            ],
            options={
                'db_table': 'monitors_monitorcheck',
                'ordering': ['-checked_at'],
            },
        ),
        migrations.AddIndex(
            model_name='monitorcheck',
            index=models.Index(fields=['monitor', '-checked_at'], name='monitors_mo_monitor_5a8f0d_idx'),
        ),
    ]
