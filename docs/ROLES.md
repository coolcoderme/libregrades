# LibreGrades Roles & Permissions

## Roles

| Role | Description |
|------|-------------|
| `student` | Views own grades, schedule, credits, medical (read), emergency contacts, behavior (if visible) |
| `parent` | Views linked children's data; manages email alert preferences |
| `teacher` | Gradebook entry, attendance, behavior logging; **limited** student medical + emergency for own sections |
| `counselor` | Student search, full medical/emergency, transcripts |
| `school_admin` | Full school data, user management |
| `district_admin` | All schools in district, Django admin access |

## Student medical access levels

| Data | Student | Parent | Teacher (own sections) | Counselor | School/District admin |
|------|---------|--------|------------------------|-----------|------------------------|
| Allergies | Yes | Yes | Yes | Yes | Yes |
| Medications | Yes | Yes | Yes | Yes | Yes |
| Medical conditions | Yes | Yes | Yes | Yes | Yes |
| Doctor name/phone | Yes | Yes | Yes | Yes | Yes |
| Emergency contacts | Yes | Yes | Yes | Yes | Yes |
| Immunizations | Yes | Yes | **No** | Yes | Yes |
| Insurance / nurse notes | Yes | Yes | **No** | Yes | Yes |

Teachers reach student medical and emergency links from the **gradebook** (student name column).

Staff (teachers, admins) also have **My Medical** for their own employee health record.

Permissions are enforced in the REST API and Django views — not UI-only.

## Parent–student linking

Parents link children using the student ID and the last 4 characters of the student ID as verification code.

## FERPA notes

- Medical and emergency data are restricted by role and enrollment.
- Audit logs record sensitive medical views.
- Deploy HTTPS in production.
