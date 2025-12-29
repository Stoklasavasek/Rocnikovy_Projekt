# Generated manually - změna related_quiz_id na ForeignKey

from django.db import migrations, models
import django.db.models.deletion


def migrate_quiz_data(apps, schema_editor):
    """Migruje data z related_quiz_id na related_quiz."""
    EducationalMaterial = apps.get_model('home', 'EducationalMaterial')
    Quiz = apps.get_model('quiz', 'Quiz')
    
    for material in EducationalMaterial.objects.all():
        # Použijeme related_quiz_id, který Django automaticky vytvoří jako _id verzi ForeignKey
        if hasattr(material, 'related_quiz_id') and material.related_quiz_id:
            try:
                quiz = Quiz.objects.get(id=material.related_quiz_id)
                # Django automaticky vytvoří related_quiz_id z related_quiz, takže jen nastavíme related_quiz
                material.related_quiz = quiz
                material.save(update_fields=['related_quiz'])
            except Quiz.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0001_initial'),
        ('home', '0003_educationalmaterial'),
    ]

    operations = [
        # Použijeme SeparateDatabaseAndState, protože sloupec už existuje v databázi
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Přidání ForeignKey constraint na existující sloupec
                migrations.RunSQL(
                    sql="""
                        DO $$ 
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint 
                                WHERE conname = 'home_educationalmaterial_related_quiz_id_fk'
                            ) THEN
                                ALTER TABLE home_educationalmaterial 
                                ADD CONSTRAINT home_educationalmaterial_related_quiz_id_fk 
                                FOREIGN KEY (related_quiz_id) REFERENCES quiz_quiz(id) 
                                ON DELETE SET NULL;
                            END IF;
                        END $$;
                    """,
                    reverse_sql="ALTER TABLE home_educationalmaterial DROP CONSTRAINT IF EXISTS home_educationalmaterial_related_quiz_id_fk;",
                ),
            ],
            state_operations=[
                # Přidání ForeignKey pole do Django state (použije existující sloupec)
                migrations.AddField(
                    model_name='educationalmaterial',
                    name='related_quiz',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='educational_materials',
                        to='quiz.quiz',
                        verbose_name='Související kvíz',
                        db_column='related_quiz_id',
                    ),
                ),
            ],
        ),
    ]



