from rest_framework import serializers

from apps.emergency.models import EmergencyContact
from apps.medical.models import Allergy, Immunization, MedicalCondition, MedicalRecord, Medication


class AllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergy
        fields = ("id", "allergen", "severity", "reaction")


class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = ("id", "name", "dosage", "frequency", "notes")


class MedicalConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalCondition
        fields = ("id", "condition", "description", "is_active")


class ImmunizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Immunization
        fields = ("id", "vaccine", "date_administered", "dose_number")


class MedicalRecordSerializer(serializers.ModelSerializer):
    allergies = AllergySerializer(many=True, read_only=True)
    medications = MedicationSerializer(many=True, read_only=True)
    medical_conditions = MedicalConditionSerializer(many=True, read_only=True)
    immunizations = ImmunizationSerializer(many=True, read_only=True)

    class Meta:
        model = MedicalRecord
        fields = (
            "id",
            "doctor_name",
            "doctor_phone",
            "insurance_provider",
            "insurance_policy",
            "nurse_notes",
            "allergies",
            "medications",
            "medical_conditions",
            "immunizations",
        )


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = (
            "id",
            "name",
            "relationship",
            "phone_primary",
            "phone_secondary",
            "email",
            "priority",
            "is_authorized_pickup",
        )
