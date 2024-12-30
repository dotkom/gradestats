from itertools import groupby
from operator import itemgetter

from grades.models import Semester, Course

from clients.nsd import NSDGradeClient

from services.course_service import CourseService

from typing import List


class GradeService:
    grade_client = NSDGradeClient()
    course_service = CourseService()
    semester_map = {
        "1": Semester.SPRING,
        "2": Semester.SUMMER,
        "3": Semester.AUTUMN,
    }

    def get_grade_data_for_semester(
        self, code, year, semester: Semester, grades: List[dict] = None
    ):
        if not grades:
            grades = self.grade_client.get_grades_for_semester(code, year, semester)

        grade_data = self.grade_client.build_grade_data_from_results(
            grades, code, year, semester
        )

        return grade_data

    def get_grades_data_for_course(self, course_code, nhd_grades: List[dict] = None):
        if nhd_grades is None:
            nhd_grades = self.grade_client.get_grades_for_course(course_code)

        if not nhd_grades:
            return []

        nhd_grades = sorted(nhd_grades, key=itemgetter("Årstall", "Semester"))

        grades_data = [
            self.get_grade_data_for_semester(
                course_code, year, self.semester_map[semester_key], list(grade)
            )
            for (year, semester_key), grade in groupby(
                nhd_grades, key=itemgetter("Årstall", "Semester")
            )
        ]

        return grades_data

    def create_or_update_grades_for_semester(
        self, course_code, year, semester: Semester
    ):
        if not Course.all_objects.filter(code=course_code).exists():
            raise ValueError(f"Course {course_code} does not exist")

        grade_data = self.get_grade_data_for_semester(course_code, year, semester)

        if not grade_data:
            print(
                f"Course {course_code} has no grades for year {year}, semester {semester}"
            )
            return None

        return self.grade_client.build_grade_from_data(grade_data)

    def create_or_update_grades_for_course(
        self, course_code, nhd_grades: List[dict] = None
    ):
        if not Course.all_objects.filter(code=course_code).exists():
            raise ValueError(f"Course {course_code} does not exist")

        grades_data = self.get_grades_data_for_course(course_code, nhd_grades)

        if not grades_data:
            print(f"Course {course_code} has no grades")
            return []

        return [
            self.grade_client.build_grade_from_data(grade_data)
            for grade_data in grades_data
        ]
