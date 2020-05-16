# Generated by Django 3.0 on 2020-05-01 13:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grades", "0004_faculty"),
    ]

    operations = [
        migrations.RemoveField(model_name="faculty", name="name",),
        migrations.AddField(
            model_name="faculty",
            name="english_name",
            field=models.CharField(
                default="", max_length=256, verbose_name="Engelsk navn"
            ),
        ),
        migrations.AddField(
            model_name="faculty",
            name="norwegian_name",
            field=models.CharField(
                default="", max_length=256, verbose_name="Norsk navn"
            ),
        ),
        migrations.AlterField(
            model_name="faculty",
            name="short_name",
            field=models.CharField(
                default="", max_length=32, verbose_name="Forkortelse"
            ),
        ),
    ]