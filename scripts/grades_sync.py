# -*- coding: utf-8 -*-

import os
import django
import requests
from operator import itemgetter
from itertools import groupby
import re
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gradestats.settings")
django.setup()

from services.course_service import CourseService
from services.grade_service import GradeService

from grades.models import Faculty, Department
from clients.nsd import NSDGradeClient, NSDCourseClient

session = requests.session()


def validate_course_code(code):
    return re.match(r"^[a-zA-Z0-9-_\sæøå]+$", code)


def main():
    course_service = CourseService()
    grade_service = GradeService()
    nsd_grade_client = NSDGradeClient()
    nsd_course_client = NSDCourseClient()

    faculties = Faculty.objects.all()
    departments = Department.objects.all()

    grades = nsd_grade_client.get_all_grades()
    courses = nsd_course_client.get_all_courses()

    for course_code, course_grades in groupby(grades, key=itemgetter("Emnekode")):
        # Don't sync courses with special-character codes
        if not validate_course_code(course_code):
            print(f"Course {course_code} has invalid code. Skipping")
            continue

        print(f"Syncing course {course_code}")

        course_grades = list(course_grades)
        course_code = course_code.rsplit("-", 1)[0]

        course_data = course_service.get_course_data(
            course_code, courses, course_grades, faculties, departments
        )

        if not course_data:
            print(f"Skipping course {course_code}")
            continue

        course_service.create_or_update_course_from_data(course_data)

        grade_service.create_or_update_grades_for_course(course_code, course_grades)


if __name__ == "__main__":
    main()
