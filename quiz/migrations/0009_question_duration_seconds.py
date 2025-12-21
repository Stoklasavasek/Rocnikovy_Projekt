from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0008_question_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="duration_seconds",
            field=models.PositiveIntegerField(default=20, help_text="Čas na odpověď v sekundách"),
        ),
    ]

