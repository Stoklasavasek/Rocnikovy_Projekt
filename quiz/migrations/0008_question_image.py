from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0006_quizsession_hash_delete_quizpage"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="image",
            field=models.ImageField(
                upload_to="question_images/", null=True, blank=True
            ),
        ),
    ]


