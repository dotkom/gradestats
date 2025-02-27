# Generated by Django 3.0 on 2020-05-17 12:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("grades", "0022_course_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="grade",
            name="semester",
            field=models.CharField(
                choices=[("SPRING", "Vår"), ("SUMMER", "Sommer"), ("AUTUMN", "Høst")],
                default="SPRING",
                max_length=32,
                verbose_name="Semester",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="grade",
            name="year",
            field=models.PositiveSmallIntegerField(default=2020, verbose_name="År"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="grade",
            name="semester_code",
            field=models.CharField(max_length=10, verbose_name="Semesterkode"),
        ),
    ]
