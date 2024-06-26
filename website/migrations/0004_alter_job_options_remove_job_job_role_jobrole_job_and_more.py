# Generated by Django 5.0.3 on 2024-03-31 01:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0003_alter_job_state'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='job',
            options={},
        ),
        migrations.RemoveField(
            model_name='job',
            name='job_role',
        ),
        migrations.AddField(
            model_name='jobrole',
            name='job',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='job_roles', to='website.job'),
            preserve_default=False,
        ),
        migrations.AlterModelTable(
            name='job',
            table=None,
        ),
    ]
