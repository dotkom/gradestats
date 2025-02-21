from typing import List
from django.core.mail import send_mail
from django.conf import settings

from .models import Course, Report, Grade


def calculate_average_grade(grades: List[Grade]):
    average = 0
    attendees = 0
    for grade in grades:
        attendees += grade.get_num_attendees()
        average += grade.average_grade * grade.get_num_attendees()
    if attendees == 0:
        return 0.0
    else:
        average /= attendees
        return average


def calculate_total_attendees(grades: List[Grade]):
    attendees = 0
    for grade in grades:
        attendees += grade.attendee_count

    return attendees


def update_course_stats(course: Course):
    grades = Grade.all_objects.filter(course_id=course.id)
    average = calculate_average_grade(grades)
    course.average = average

    attendee_count = calculate_total_attendees(grades)
    course.attendee_count = attendee_count

    course.save()


def send_report(report: Report):
    send_mail(
        subject=report.subject,
        message=report.email_description,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[settings.REPORTS_EMAIL],
        fail_silently=False,
    )
