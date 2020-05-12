# Generated by Django 3.0 on 2020-05-01 14:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("grades", "0005_auto_20200501_1334"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
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
                    "key",
                    models.IntegerField(
                        help_text="Nøkkel fra Karstat",
                        unique=True,
                        verbose_name="Nøkkel",
                    ),
                ),
                (
                    "norwegian_name",
                    models.CharField(
                        default="", max_length=256, verbose_name="Norsk navn"
                    ),
                ),
                (
                    "english_name",
                    models.CharField(
                        default="", max_length=256, verbose_name="Engelsk navn"
                    ),
                ),
                (
                    "short_name",
                    models.CharField(
                        default="", max_length=32, verbose_name="Forkortelse"
                    ),
                ),
                (
                    "faculty",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="departments",
                        to="grades.Faculty",
                    ),
                ),
            ],
            options={
                "verbose_name": "Institutt",
                "verbose_name_plural": "Institutter",
                "ordering": ("key",),
            },
        ),
    ]
