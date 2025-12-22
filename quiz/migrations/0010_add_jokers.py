# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0009_question_duration_seconds"),
    ]

    operations = [
        migrations.AddField(
            model_name="quiz",
            name="jokers_count",
            field=models.PositiveIntegerField(default=0, help_text="Počet žolíků za celou hru (0-3)"),
        ),
        migrations.AddField(
            model_name="participant",
            name="jokers_used",
            field=models.PositiveIntegerField(default=0, help_text="Počet použitých žolíků"),
        ),
    ]

