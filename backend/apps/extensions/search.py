from django.db.models import Q

from apps.grades.models import Assignment
from apps.scheduling.models import Course, Section
from apps.students.models import StudentProfile


def global_search(user, query: str, limit=20):
    q = query.strip()
    if len(q) < 2:
        return {"students": [], "sections": [], "assignments": []}
    students = StudentProfile.objects.filter(
        Q(user__first_name__icontains=q)
        | Q(user__last_name__icontains=q)
        | Q(student_id__icontains=q)
    )[:limit]
    sections = Section.objects.filter(
        Q(course__code__icontains=q) | Q(course__name__icontains=q)
    ).select_related("course")[:limit]
    assignments = Assignment.objects.filter(title__icontains=q).select_related("section__course")[:limit]
    return {
        "students": students,
        "sections": sections,
        "assignments": assignments,
        "courses": Course.objects.filter(Q(code__icontains=q) | Q(name__icontains=q))[:limit],
    }
