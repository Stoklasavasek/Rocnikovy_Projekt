# Generated manually for EducationalMaterial model

from django.db import migrations, models
import django.db.models.deletion
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0095_groupsitepermission'),
        ('home', '0002_create_homepage'),
    ]

    operations = [
        migrations.CreateModel(
            name='EducationalMaterial',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('related_quiz_id', models.PositiveIntegerField(blank=True, help_text='ID kvízu, ke kterému se materiál vztahuje (volitelné)', null=True, verbose_name='ID souvisejícího kvízu')),
                ('material_type', models.CharField(choices=[('text', 'Textový materiál'), ('video', 'Video'), ('link', 'Externí odkaz'), ('document', 'Dokument')], default='text', max_length=50, verbose_name='Typ materiálu')),
                ('content', wagtail.fields.RichTextField(blank=True, verbose_name='Obsah materiálu')),
                ('external_url', models.URLField(blank=True, help_text='URL pro externí materiál (video, dokument, atd.)', verbose_name='Externí URL')),
                ('show_before_quiz', models.BooleanField(default=True, help_text='Zobrazit materiál před kvízem', verbose_name='Zobrazit před kvízem')),
                ('show_after_quiz', models.BooleanField(default=False, help_text='Zobrazit materiál po kvízu', verbose_name='Zobrazit po kvízu')),
            ],
            options={
                'verbose_name': 'Vzdělávací materiál',
                'verbose_name_plural': 'Vzdělávací materiály',
            },
            bases=('wagtailcore.page',),
        ),
    ]

