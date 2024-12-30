from datetime import datetime
from clients.nsd import NSDCourseClient, NSDGradeClient
from clients.course_pages import CoursePagesClient


from typing import List

from grades.models import Course, Faculty, Department


class CourseService:
    STUDY_LEVEL_MAP = {"LN": 100, "VS": 300, "HN": 500, "FU": 900, "AR": 350, "50": 50}

    course_client = NSDCourseClient()
    grade_client = NSDGradeClient()
    course_page_client = CoursePagesClient()

    def exclude_empty_values(self, data):
        return {k: v for k, v in data.items() if v not in [None, ""]}

    def get_taught_to(
        self, code, course_data: List[dict] = None, grades: List[dict] = None
    ):
        course_data = course_data or self.course_client.get_course(code)
        grades = grades or self.grade_client.get_grades_for_course(code)

        discontinued_courses = [
            course for course in course_data if course["Status"] in {"3", "4"}
        ]
        if not discontinued_courses:
            return 0

        discontinued_year = int(
            max(discontinued_courses, key=lambda course: course["Årstall"])["Årstall"]
        )

        latest_course_year = max(
            (int(course["Årstall"]) for course in course_data),
            default=float("-inf"),
        )
        latest_grade_year = max(
            (int(grade["Årstall"]) for grade in grades), default=float("-inf")
        )

        if max(latest_course_year, latest_grade_year) > discontinued_year:
            return 0

        # Course discontinued year before it got status 3 or 4
        return discontinued_year - 1

    def get_taught_from(
        self, code, grades: List[dict] = None, course: List[dict] = None
    ):
        grades = grades or self.grade_client.get_grades_for_course(code)
        course = course or self.course_client.get_course(code)

        if not grades and not course:
            return 0

        first_grade_year = min(
            (int(grade["Årstall"]) for grade in grades), default=float("inf")
        )
        first_course_year = min(
            (int(course_item["Årstall"]) for course_item in course),
            default=float("inf"),
        )

        if first_grade_year == float("inf") and first_course_year == float("inf"):
            return 0

        return min(first_grade_year, first_course_year)

    def get_faculty_and_department(
        self,
        faculty_code,
        faculties: List[Faculty] = None,
        departments: List[Department] = None,
    ):
        if not faculty_code:
            return None, None

        nsd_code = f"1150{faculty_code}"

        def get_first_from_queryset(queryset):
            return queryset.filter(nsd_code=nsd_code).first()

        department = get_first_from_queryset(departments or Department.objects)
        faculty = get_first_from_queryset(faculties or Faculty.objects)

        if department and not faculty:
            faculty = department.faculty

        return faculty, department

    def get_course_data_from_course_pages(
        self, code, taught_from: int, last_year_taught: int
    ):
        data = self.course_page_client.get_course_data(code)
        if data:
            return data

        default_end_year = 2000

        start_year = last_year_taught
        if start_year == 0:
            start_year = datetime.now().year

        end_year = taught_from
        if end_year == 0 or end_year > start_year:
            end_year = max(start_year - 5, default_end_year)

        try_limit = 8

        for try_count, year in enumerate(range(start_year, end_year - 1, -1), start=1):
            if try_count > try_limit:
                return None

            data = self.course_page_client.get_course_data(code, year)
            if data:
                return data

        return None

    def parse_dbh_course(self, dbh_course: List[dict], code: str):
        if not dbh_course:
            raise ValueError(f"No course data available for code {code}")

        last_course = dbh_course[-1]

        return {
            "norwegian_name": last_course.get("Emnenavn", ""),
            "english_name": "",
            "code": code,
            "credit": last_course.get("Studiepoeng", 0),
            "study_level": self.STUDY_LEVEL_MAP.get(last_course.get("Nivåkode", ""), 0),
            "taught_in_autumn": False,
            "taught_in_spring": False,
            "taught_in_english": False,
            "exam_type": "",
            "grade_type": "",
            "place": "",
        }

    def get_course_data(
        self,
        code: str,
        all_courses: List[dict] = None,
        all_grades: List[dict] = None,
        faculties: List[Faculty] = None,
        departments: List[Department] = None,
    ):
        all_courses = all_courses or []
        all_grades = all_grades or []

        dbh_grades = [grade for grade in all_grades if f"{code}-" in grade["Emnekode"]]
        dbh_course = [
            course for course in all_courses if f"{code}-" in course["Emnekode"]
        ]

        dbh_course = dbh_course or self.course_client.get_course(code)
        dbh_grades = dbh_grades or self.grade_client.get_grades_for_course(code)

        taught_from = self.get_taught_from(code, dbh_grades, dbh_course)
        last_year_taught = self.get_taught_to(code, dbh_course, dbh_grades)
        if taught_from > last_year_taught:
            last_year_taught = 0

        data = self.get_course_data_from_course_pages(
            code, taught_from, last_year_taught
        )

        if not data:
            if not dbh_course:
                print(f"No data found for course {code}")
                return None

            print("Using course data from DBH")
            data = self.parse_dbh_course(dbh_course, code)

        faculty_code = dbh_course[-1].get("Avdelingskode", None) if dbh_course else None
        faculty, department = self.get_faculty_and_department(
            faculty_code, faculties, departments
        )

        if faculty:
            data["faculty_code"] = faculty.faculty_id
        if department:
            data["department_id"] = department.id

        if dbh_course:
            data["last_year_taught"] = last_year_taught
            data["taught_from"] = taught_from

        return data

    def create_or_update_course_from_data(self, data):
        course_code = data["code"]
        existing_course = Course.all_objects.filter(code=course_code)

        if existing_course.exists():
            # Avoid overriding fields with empty values
            data = self.exclude_empty_values(data)

            print(f"Updating existing course with code: {course_code}")
            existing_course.update(**data)
            return existing_course.first()
        else:
            print(f"Creating new course with code: {course_code}")
            new_course = Course.objects.create(**data)
            return new_course

    def create_or_update_course(self, code):
        data = self.get_course_data(code)
        return self.create_or_update_course_from_data(data)
