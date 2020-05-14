# Generated by Django 3.0 on 2020-05-14 14:32

from django.db import migrations


def create_through_relations(apps, schema_editor):
    Tag = apps.get_model("grades", "Tag")
    CourseTag = apps.get_model("grades", "CourseTag")
    for tag in Tag.objects.all():
        for course in tag.courses.all():
            CourseTag.objects.create(tag=tag, course=course)


class Migration(migrations.Migration):

    dependencies = [
        ("grades", "0008_coursetag"),
    ]

    operations = [
        migrations.RunPython(
            create_through_relations, reverse_code=migrations.RunPython.noop
        ),
    ]
