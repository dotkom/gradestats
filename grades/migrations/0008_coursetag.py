# Generated by Django 3.0 on 2020-05-14 14:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("grades", "0007_report"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseTag",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_tags",
                        to="grades.Course",
                    ),
                ),
                (
                    "tag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_tags",
                        to="grades.Tag",
                    ),
                ),
            ],
            options={
                "unique_together": {("course", "tag")},
            },
        ),
    ]
