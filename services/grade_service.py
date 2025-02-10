from itertools import groupby
from operator import itemgetter

from grades.models import Semester, Course, Grade

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

    def get_grades_data_for_course(self, course_code, nsd_grades: List[dict] = None):
        if nsd_grades is None:
            nsd_grades = self.grade_client.get_grades_for_course(course_code)

        if not nsd_grades:
            return []

        nsd_grades = sorted(nsd_grades, key=itemgetter("Årstall", "Semester"))

        grades_data = [
            self.get_grade_data_for_semester(
                course_code, year, self.semester_map[semester_key], list(grade)
            )
            for (year, semester_key), grade in groupby(
                nsd_grades, key=itemgetter("Årstall", "Semester")
            )
        ]

        return grades_data

    def create_or_update_grades_for_semester(
        self, course_code, year, semester: Semester
    ):
        if not Course.all_objects.filter(code=course_code).exists():
            raise ValueError(f"Course {course_code} does not exist")

        grade_data = self.get_grade_data_for_semester(course_code, year, semester)
        grade_data = self.filter_out_conflicting_grades(
            [grade_data], Grade.all_objects.filter(course__code=course_code)
        )

        if not grade_data:
            print(
                f"Course {course_code} has no grades for year {year}, semester {semester}"
            )
            return None

        return self.grade_client.build_grade_from_data(grade_data)

    def create_or_update_grades_for_course(
        self, course_code, nsd_grades: List[dict] = None
    ):
        if not Course.all_objects.filter(code=course_code).exists():
            raise ValueError(f"Course {course_code} does not exist")

        grades_data = self.get_grades_data_for_course(course_code, nsd_grades)
        grades_data = self.filter_out_conflicting_grades(
            grades_data, Grade.all_objects.filter(course__code=course_code)
        )

        if not grades_data:
            print(f"Course {course_code} has no grades")
            return []

        return [
            self.grade_client.build_grade_from_data(grade_data)
            for grade_data in grades_data
        ]

    def filter_out_conflicting_grades(
        self, grades_data: List[dict], existing_grades_data: List[Grade]
    ):
        filtered_grades = []

        grades_data.sort(key=lambda grade: int(grade["year"]))

        summer_represents_spring, summer_represents_autumn = (
            self.get_summer_semester_mapping(existing_grades_data)
        )

        # Allow overriding nsd data
        last_year_with_karstat_data = 2021

        for year, grades_by_year in groupby(grades_data, key=itemgetter("year")):
            grades_by_year = list(grades_by_year)
            existing_grades_by_year = [
                grade for grade in existing_grades_data if grade.year == int(year)
            ]

            if int(year) > last_year_with_karstat_data or not existing_grades_by_year:
                filtered_grades.extend(grades_by_year)
                continue

            existing_grades_semesters = {
                grade.semester for grade in existing_grades_by_year
            }
            has_existing_summer_grades = "SUMMER" in existing_grades_semesters
            has_existing_spring_grades = "SPRING" in existing_grades_semesters
            has_existing_autumn_grades = "AUTUMN" in existing_grades_semesters

            grades_by_semester = {
                semester: [
                    grade for grade in grades_by_year if grade["semester"] == semester
                ]
                for semester in ["SPRING", "AUTUMN", "SUMMER"]
            }

            if (
                grades_by_semester["SPRING"]
                and not has_existing_spring_grades
                and (not has_existing_summer_grades or summer_represents_autumn)
            ):
                filtered_grades.extend(grades_by_semester["SPRING"])

            if (
                grades_by_semester["AUTUMN"]
                and not has_existing_autumn_grades
                and (not has_existing_summer_grades or summer_represents_spring)
            ):
                filtered_grades.extend(grades_by_semester["AUTUMN"])

            if grades_by_semester["SUMMER"] and not has_existing_summer_grades:
                filtered_grades.extend(grades_by_semester["SUMMER"])

        return filtered_grades

    def get_summer_semester_mapping(self, course_grades: List[Grade]):
        distinct_years = set(grade.year for grade in course_grades)

        UNKNOWN = None

        summer_represents_spring = UNKNOWN
        summer_represents_autumn = UNKNOWN

        for year in distinct_years:
            semesters = {
                grade.semester for grade in course_grades if grade.year == year
            }

            has_spring = "SPRING" in semesters
            has_summer = "SUMMER" in semesters
            has_autumn = "AUTUMN" in semesters

            if not has_summer:
                continue

            if has_autumn:
                summer_represents_autumn = False
            elif has_spring and summer_represents_autumn is UNKNOWN:
                summer_represents_autumn = True

            if has_spring:
                summer_represents_spring = False
            elif has_autumn and summer_represents_spring is UNKNOWN:
                summer_represents_spring = True

        return summer_represents_spring, summer_represents_autumn
