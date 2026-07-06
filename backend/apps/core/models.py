from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class District(TimeStampedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class School(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="schools")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["district", "code"]]

    def __str__(self):
        return self.name


class AcademicYear(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="academic_years")
    name = models.CharField(max_length=64)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class Term(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="terms")
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="terms", null=True, blank=True
    )
    name = models.CharField(max_length=64)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.school.name} — {self.name}"


class ServerIdentity(TimeStampedModel):
    """Unique 6-digit code identifying this LibreGrades installation."""

    code = models.CharField(max_length=6, unique=True, editable=False)

    class Meta:
        verbose_name = "server identity"
        verbose_name_plural = "server identity"

    def __str__(self):
        return self.code
