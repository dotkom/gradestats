from typing import List
from django.db.models import TextChoices
from json import JSONDecodeError

from .client import Client

from grades.models import Semester, Course, Grade

"""
API documentation can be found at:
https://dbh.hkdir.no/static/files/dokumenter/api/api_dokumentasjon.pdf

Or table documentation found at:
https://dbh.hkdir.no/datainnhold/tabell-dokumentasjon
"""


class FilterType(TextChoices):
    TOP = "top", "Topp"
    ALL = "all", "Alle"
    ITEM = "item", "Enkelt enhet"
    BETWEEN = "between", "Mellom"
    LIKE = "like", "Lik"
    LESSTHAN = "lessthan", "Mindre enn"


class NSDClient(Client):
    base_url = "https://dbh.hkdir.no"
    institution_id = 1150  # ID for NTNU in DBH databases
    api_version = 1
    status_line = False  # Should extra information about the API response be included?
    code_text = True  # Should names of related resources be included?
    decimal_separator = "."
    table_id = 0

    def __init__(self):
        super().__init__()
        self.session.headers.update({"Content-type": "application/json"})

    def get_json_table_url(self):
        return f"{self.base_url}/api/Tabeller/hentJSONTabellData"

    def create_filter(self, name: str, filter_type: FilterType, values, exclude=[""]):
        return {
            "variabel": name,
            "selection": {
                "filter": filter_type,
                "values": values,
                "exclude": exclude,
            },
        }

    def get_institution_filter(self):
        return self.create_filter(
            name="Institusjonskode",
            filter_type=FilterType.ITEM,
            values=[str(self.institution_id)],
        )

    def get_course_filter(self, course_code: str):
        # Filter course code by SQL 'like' since course codes in DBH include a version number in the string.
        course_code_likeness = f"{course_code}-%"
        return self.create_filter(
            name="Emnekode", filter_type=FilterType.LIKE, values=[course_code_likeness]
        )

    def get_year_filter(self, year: int):
        return self.create_filter(
            name="Årstall", filter_type=FilterType.ITEM, values=[str(year)]
        )

    def get_semester_id(self, semester: Semester):
        lookup = {
            Semester.SPRING: 1,
            Semester.SUMMER: 2,  # DBH does not actually work for SUMMER semester!
            Semester.AUTUMN: 3,
        }
        return lookup[semester]

    def get_semester_filter(self, semester: Semester):
        semester_id = self.get_semester_id(semester)
        return self.create_filter(
            name="Semester", filter_type=FilterType.ITEM, values=[semester_id]
        )

    def build_query(
        self,
        group_by: List[str],
        sort_by: List[str],
        filters: List[str],
        limit: int = None,
    ):
        query = {
            "tabell_id": self.table_id,
            "api_versjon": self.api_version,
            "statuslinje": "J" if self.status_line else "N",
            "kodetekst": "J" if self.code_text else "N",
            "desimal_separator": self.decimal_separator,
            "groupBy": group_by,
            "sortBy": sort_by,
            "variabler": ["*"],
            "filter": filters,
        }

        if limit:
            query["begrensning"] = str(limit)

        return query

    def get_result_from_query(self, query):
        url = self.get_json_table_url()
        response = self.session.post(url, json=query)

        try:
            results = response.json()
        except JSONDecodeError:
            results = []
        return results


class NSDGradeClient(NSDClient):
    table_id = 308

    def resolve_result_for_grade(self, results, letter: str):
        grade_results = [
            result for result in results if result.get("Karakter") == letter
        ]
        if len(grade_results) == 0:
            return 0
        elif len(grade_results) > 1:
            raise Exception("Found more than a single grade entry for a course")

        grade_result = grade_results[0]
        return int(grade_result.get("Antall kandidater totalt"))

    def build_grade_data_from_results(
        self, results, course_code: str, year: int, semester: Semester
    ):
        average_grade = 0
        passed = self.resolve_result_for_grade(results, "G")
        failed = self.resolve_result_for_grade(results, "H")
        a = self.resolve_result_for_grade(results, "A")
        b = self.resolve_result_for_grade(results, "B")
        c = self.resolve_result_for_grade(results, "C")
        d = self.resolve_result_for_grade(results, "D")
        e = self.resolve_result_for_grade(results, "E")
        f = self.resolve_result_for_grade(results, "F")

        student_count = a + b + c + d + e + f

        is_pass_fail = any(map(lambda number: number != 0, [passed, failed]))
        is_graded = any(map(lambda number: number != 0, [a, b, c, d, e, f]))

        if is_pass_fail and is_graded:
            print(
                "Course is both pass/failed and graded by letters. Ignoring pass/fail"
            )
            is_pass_fail = False

        if is_pass_fail:
            average_grade = 0
            a = 0
            b = 0
            c = 0
            d = 0
            e = 0
            f = failed
        else:
            if student_count > 0:
                average_grade = (a * 5.0 + b * 4 + c * 3 + d * 2 + e) / student_count
            passed = 0

        course_id = Course.all_objects.filter(code=course_code).values("id").first()
        if course_id:
            course_id = course_id["id"]
        else:
            raise ValueError(f"Course with code {course_code} does not exist")

        data = {
            "a": a,
            "b": b,
            "c": c,
            "d": d,
            "e": e,
            "f": f,
            "average_grade": average_grade,
            "passed": passed,
            "course_id": course_id,
            "semester": str(semester),
            "year": year,
        }

        return data

    def build_grade_from_data(self, grade_data):
        course_id = grade_data.get("course_id")
        semester = grade_data.get("semester")
        year = grade_data.get("year")

        # Don't import grades with no candidates
        if (
            grade_data.get("average_grade") == 0
            and grade_data.get("passed") == 0
            and grade_data.get("f") == 0
        ):
            return

        try:
            grade = Grade.all_objects.get(
                course_id=course_id,
                semester=semester,
                year=year,
            )
            Grade.all_objects.filter(
                course_id=course_id,
                semester=semester,
                year=year,
            ).update(**grade_data)
            grade.refresh_from_db()
        except Grade.DoesNotExist:
            grade = Grade.objects.create(**grade_data)

        return Grade.all_objects.get(pk=grade.id)

    def get_grades_for_semester(self, course_code: str, year: int, semester: Semester):
        group_by = ["Institusjonskode", "Avdelingskode", "Emnekode", "Karakter"]
        sort_by = ["Institusjonskode", "Avdelingskode"]
        filters = [
            self.get_semester_filter(semester),
            self.get_institution_filter(),
            self.get_course_filter(course_code),
            self.get_year_filter(year),
        ]

        query = self.build_query(group_by, sort_by, filters)
        return self.get_result_from_query(query)

    def get_grades_for_course(self, course_code: str):
        group_by = [
            "Institusjonskode",
            "Emnekode",
            "Karakter",
            "Årstall",
            "Semester",
            "Avdelingskode",
        ]
        sort_by = ["Emnekode", "Årstall", "Semester"]
        filters = [self.get_institution_filter(), self.get_course_filter(course_code)]

        query = self.build_query(group_by, sort_by, filters)
        return self.get_result_from_query(query)

    def get_all_grades(self):
        group_by = [
            "Institusjonskode",
            "Emnekode",
            "Karakter",
            "Årstall",
            "Semester",
            "Avdelingskode",
        ]
        sort_by = ["Emnekode", "Årstall", "Semester"]
        filters = [self.get_institution_filter()]

        query = self.build_query(group_by, sort_by, filters)
        return self.get_result_from_query(query)


class NSDCourseClient(NSDClient):
    table_id = 208

    def get_task_filter(self):
        return self.create_filter(
            name="Oppgave (ny fra h2012)",
            filter_type=FilterType.ALL,
            values=["*"],
            exclude=["1", "2"],
        )

    def get_status_filter(self, status):
        return self.create_filter(
            name="Status", filter_type=FilterType.ITEM, values=status
        )

    def get_course(self, code):
        group_by = []
        sort_by = ["Årstall", "Semester"]
        filters = [
            self.get_institution_filter(),
            self.get_task_filter(),
            self.get_course_filter(code),
        ]

        query = self.build_query(group_by, sort_by, filters)
        return self.get_result_from_query(query)

    def get_all_courses(self):
        group_by = []
        sort_by = ["Emnekode", "Årstall", "Semester"]
        filters = [self.get_institution_filter(), self.get_task_filter()]

        query = self.build_query(group_by, sort_by, filters)
        return self.get_result_from_query(query)
