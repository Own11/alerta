from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='notify_email',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='user',
            name='notify_push',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='user',
            name='notify_slack',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='user',
            name='notify_telegram',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='user',
            name='report_frequency',
            field=models.CharField(
                choices=[('off', 'Выключено'), ('daily', 'Ежедневно'), ('weekly', 'Еженедельно')],
                default='daily',
                max_length=10,
            ),
        ),
    ]
