import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_student_medical_to_user(apps, schema_editor):
    StudentProfile = apps.get_model("students", "StudentProfile")
    MedicalRecord = apps.get_model("medical", "MedicalRecord")
    for model_name in ("Allergy", "Medication", "MedicalCondition", "Immunization"):
        Model = apps.get_model("medical", model_name)
        for row in Model.objects.exclude(student_id=None):
            student = StudentProfile.objects.filter(pk=row.student_id).first()
            if student:
                row.user_id = student.user_id
                row.save(update_fields=["user_id"])
    for record in MedicalRecord.objects.exclude(student_id=None):
        student = StudentProfile.objects.filter(pk=record.student_id).first()
        if student:
            record.user_id = student.user_id
            record.save(update_fields=["user_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("medical", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="allergy",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="allergies",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="immunization",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="immunizations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="medicalcondition",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="medical_conditions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="medicalrecord",
            name="user",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="medical_record",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="medication",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="medications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(copy_student_medical_to_user, migrations.RunPython.noop),
        migrations.RemoveField(model_name="allergy", name="student"),
        migrations.RemoveField(model_name="immunization", name="student"),
        migrations.RemoveField(model_name="medicalcondition", name="student"),
        migrations.RemoveField(model_name="medicalrecord", name="student"),
        migrations.RemoveField(model_name="medication", name="student"),
        migrations.AlterField(
            model_name="allergy",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="allergies",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="immunization",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="immunizations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="medicalcondition",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="medical_conditions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="medicalrecord",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="medical_record",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="medication",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="medications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
