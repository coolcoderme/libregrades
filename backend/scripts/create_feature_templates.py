"""One-off script to create portal templates for features 1-14."""
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "portal"

FILES = {
    "announcements.html": """{% extends "portal/base.html" %}
{% block title %}Announcements{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h1 class="h3 mb-0">Announcements</h1>
  {% if role == 'teacher' or role == 'school_admin' or role == 'district_admin' or role == 'counselor' %}
  <a href="{% url 'portal:announcement_create' %}" class="btn btn-primary btn-sm">New announcement</a>
  {% endif %}
</div>
{% for a in announcements %}
<div class="card mb-3">
  <div class="card-body">
    <h2 class="h5 card-title">{{ a.title }}</h2>
    <p class="text-muted small mb-2">{{ a.author.display_name }} · {{ a.created_at|date:"M j, Y g:i A" }} · {{ a.get_scope_display }}</p>
    <p class="card-text mb-0">{{ a.body|linebreaksbr }}</p>
  </div>
</div>
{% empty %}
<p class="text-muted">No announcements yet.</p>
{% endfor %}
{% endblock %}
""",
    "announcement_form.html": """{% extends "portal/base.html" %}
{% block title %}New announcement{% endblock %}
{% block content %}
<h1 class="h3 mb-4">New announcement</h1>
<form method="post" class="col-lg-8">
  {% csrf_token %}
  <div class="mb-3">
    <label class="form-label">Title</label>
    <input type="text" name="title" class="form-control" required>
  </div>
  <div class="mb-3">
    <label class="form-label">Body</label>
    <textarea name="body" class="form-control" rows="5" required></textarea>
  </div>
  <div class="mb-3">
    <label class="form-label">Scope</label>
    <select name="scope" class="form-select">
      <option value="school">School-wide</option>
      <option value="district">District-wide</option>
      <option value="section">Class section</option>
    </select>
  </div>
  <div class="mb-3">
    <label class="form-label">Section (if class scope)</label>
    <select name="section_id" class="form-select">
      <option value="">—</option>
      {% for s in sections %}
      <option value="{{ s.id }}">{{ s.course.code }} — Section {{ s.section_number }}</option>
      {% endfor %}
    </select>
  </div>
  <button type="submit" class="btn btn-primary">Publish</button>
  <a href="{% url 'portal:announcements' %}" class="btn btn-outline-secondary">Cancel</a>
</form>
{% endblock %}
""",
    "messages.html": """{% extends "portal/base.html" %}
{% block title %}Messages{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h1 class="h3 mb-0">Inbox</h1>
  <a href="{% url 'portal:message_compose' %}" class="btn btn-primary btn-sm">Compose</a>
</div>
<table class="table table-hover">
  <thead><tr><th>From</th><th>Subject</th><th>Student</th><th>Date</th></tr></thead>
  <tbody>
    {% for m in messages %}
    <tr class="{% if not m.is_read %}fw-semibold{% endif %}">
      <td>{{ m.sender.display_name }}</td>
      <td>{{ m.subject }}</td>
      <td>{% if m.student %}{{ m.student.full_name }}{% else %}—{% endif %}</td>
      <td>{{ m.created_at|date:"M j, Y" }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted">No messages.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
""",
    "message_compose.html": """{% extends "portal/base.html" %}
{% block title %}Compose message{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Compose message</h1>
{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
<form method="post" class="col-lg-8">
  {% csrf_token %}
  <div class="mb-3">
    <label class="form-label">Regarding student</label>
    <select name="student_id" class="form-select" required>
      {% for s in students %}
      <option value="{{ s.id }}">{{ s.full_name }} ({{ s.student_id }})</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label class="form-label">Subject</label>
    <input type="text" name="subject" class="form-control" required>
  </div>
  <div class="mb-3">
    <label class="form-label">Message</label>
    <textarea name="body" class="form-control" rows="6" required></textarea>
  </div>
  <button type="submit" class="btn btn-primary">Send</button>
</form>
{% endblock %}
""",
    "due_this_week.html": """{% extends "portal/base.html" %}
{% block title %}Due this week{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Due this week — {{ student.full_name }}</h1>
<div class="row g-4">
  <div class="col-lg-7">
    <h2 class="h5">Upcoming assignments</h2>
    <table class="table table-sm">
      <thead><tr><th>Course</th><th>Assignment</th><th>Due</th></tr></thead>
      <tbody>
        {% for a in upcoming %}
        <tr>
          <td>{{ a.section.course.code }}</td>
          <td>{{ a.title }}</td>
          <td>{{ a.due_date }}</td>
        </tr>
        {% empty %}
        <tr><td colspan="3" class="text-muted">Nothing due in the next 7 days.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="col-lg-5">
    <div class="card mb-3">
      <div class="card-body">
        <h6 class="card-subtitle text-muted">Missing work</h6>
        <p class="display-6 mb-0">{{ missing_count }}</p>
      </div>
    </div>
    <h2 class="h6">Recent posted grades</h2>
    <ul class="list-group list-group-flush">
      {% for g in recent_grades %}
      <li class="list-group-item px-0">{{ g.assignment.section.course.code }} — {{ g.assignment.title }}: {% if g.points != None %}{{ g.points }}/{{ g.assignment.max_points }}{% else %}—{% endif %}</li>
      {% empty %}
      <li class="list-group-item px-0 text-muted">No recent grades.</li>
      {% endfor %}
    </ul>
    <a href="{% url 'portal:report_card' student.id %}" class="btn btn-outline-primary btn-sm mt-3">Download report card (PDF)</a>
  </div>
</div>
{% endblock %}
""",
    "csv_tools.html": """{% extends "portal/base.html" %}
{% block title %}CSV tools{% endblock %}
{% block content %}
<h1 class="h3 mb-4">CSV import / export</h1>
{% if result %}
<div class="alert alert-info">Created: {{ result.created }}, updated: {{ result.updated }}{% if result.errors %}, errors: {{ result.errors|length }}{% endif %}</div>
{% endif %}
<div class="row g-4">
  <div class="col-md-6">
    <div class="card">
      <div class="card-body">
        <h2 class="h6">Import students</h2>
        <form method="post" enctype="multipart/form-data">
          {% csrf_token %}
          <input type="hidden" name="action" value="import_students">
          <input type="file" name="file" accept=".csv" class="form-control mb-2" required>
          <button type="submit" class="btn btn-primary btn-sm">Import</button>
        </form>
      </div>
    </div>
  </div>
  <div class="col-md-6">
    <div class="card">
      <div class="card-body">
        <h2 class="h6">Import enrollments</h2>
        <form method="post" enctype="multipart/form-data">
          {% csrf_token %}
          <input type="hidden" name="action" value="import_enrollments">
          <input type="file" name="file" accept=".csv" class="form-control mb-2" required>
          <button type="submit" class="btn btn-primary btn-sm">Import</button>
        </form>
      </div>
    </div>
  </div>
  <div class="col-md-6">
    <div class="card">
      <div class="card-body">
        <h2 class="h6">Export students</h2>
        <form method="post">
          {% csrf_token %}
          <input type="hidden" name="action" value="export_students">
          <button type="submit" class="btn btn-outline-secondary btn-sm">Download CSV</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
""",
    "notification_center.html": """{% extends "portal/base.html" %}
{% block title %}Notifications{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h1 class="h3 mb-0">Notifications</h1>
  <form method="post">{% csrf_token %}<button type="submit" class="btn btn-outline-secondary btn-sm">Mark all read</button></form>
</div>
<ul class="list-group">
  {% for n in notifications %}
  <li class="list-group-item {% if not n.is_read %}list-group-item-primary{% endif %}">
    <div class="fw-semibold">{{ n.title }}</div>
    <div class="small text-muted">{{ n.created_at|date:"M j, Y g:i A" }}</div>
    <div>{{ n.message }}</div>
  </li>
  {% empty %}
  <li class="list-group-item text-muted">No notifications.</li>
  {% endfor %}
</ul>
{% endblock %}
""",
    "totp_setup.html": """{% extends "portal/base.html" %}
{% block title %}Two-factor authentication{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Two-factor authentication</h1>
{% if enabled %}
<p class="text-success">2FA is enabled on your account.</p>
<form method="post" class="col-md-6">
  {% csrf_token %}
  <input type="hidden" name="action" value="disable">
  <div class="mb-3">
    <label class="form-label">Enter code to disable</label>
    <input type="text" name="token" class="form-control" inputmode="numeric" autocomplete="one-time-code" required>
  </div>
  <button type="submit" class="btn btn-danger">Disable 2FA</button>
</form>
{% else %}
<p>Scan this QR code with your authenticator app, then enter a code to enable.</p>
{% if qr_b64 %}<img src="data:image/png;base64,{{ qr_b64 }}" alt="QR code" class="mb-3" style="max-width:200px">{% endif %}
<p class="small text-muted">Manual key: <code>{{ secret }}</code></p>
<form method="post" class="col-md-6">
  {% csrf_token %}
  <input type="hidden" name="action" value="enable">
  <div class="mb-3">
    <label class="form-label">Verification code</label>
    <input type="text" name="token" class="form-control" inputmode="numeric" autocomplete="one-time-code" required>
  </div>
  <button type="submit" class="btn btn-primary">Enable 2FA</button>
</form>
{% endif %}
{% endblock %}
""",
    "totp_verify.html": """{% extends "portal/base.html" %}
{% block title %}Verify identity{% endblock %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-5">
    <div class="card shadow">
      <div class="card-body p-4">
        <h1 class="h4 mb-3">Two-factor verification</h1>
        <p class="text-muted">Enter the code from your authenticator app.</p>
        <form method="post">
          {% csrf_token %}
          <div class="mb-3">
            <input type="text" name="token" class="form-control" inputmode="numeric" autocomplete="one-time-code" autofocus required>
          </div>
          <button type="submit" class="btn btn-primary w-100">Verify</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
""",
    "at_risk.html": """{% extends "portal/base.html" %}
{% block title %}At-risk students{% endblock %}
{% block content %}
<h1 class="h3 mb-4">At-risk dashboard</h1>
<table class="table table-striped">
  <thead><tr><th>Student</th><th>Score</th><th>Flags</th><th></th></tr></thead>
  <tbody>
    {% for row in rows %}
    <tr>
      <td>{{ row.student.full_name }}</td>
      <td><span class="badge bg-warning text-dark">{{ row.score }}</span></td>
      <td>{{ row.flags|join:", " }}</td>
      <td><a href="{% url 'portal:accommodations' row.student.id %}" class="btn btn-sm btn-outline-secondary">Accommodations</a></td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted">No at-risk students flagged.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
""",
    "conference_manage.html": """{% extends "portal/base.html" %}
{% block title %}Conference slots{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Parent conference slots</h1>
<form method="post" action="{% url 'portal:conference_create' %}" class="row g-2 mb-4 col-lg-8">
  {% csrf_token %}
  <div class="col-md-4"><input type="datetime-local" name="start_at" class="form-control" required></div>
  <div class="col-md-4"><input type="datetime-local" name="end_at" class="form-control" required></div>
  <div class="col-md-3"><input type="text" name="location" class="form-control" placeholder="Location"></div>
  <div class="col-md-1"><button type="submit" class="btn btn-primary w-100">Add</button></div>
</form>
<table class="table">
  <thead><tr><th>When</th><th>Location</th><th>Status</th><th>Student</th></tr></thead>
  <tbody>
    {% for s in slots %}
    <tr>
      <td>{{ s.start_at|date:"M j, g:i A" }} – {{ s.end_at|date:"g:i A" }}</td>
      <td>{{ s.location|default:"—" }}</td>
      <td>{% if s.is_booked %}<span class="badge bg-success">Booked</span>{% else %}<span class="badge bg-secondary">Open</span>{% endif %}</td>
      <td>{% if s.student %}{{ s.student.full_name }}{% else %}—{% endif %}</td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted">No slots yet.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
""",
    "conference_book.html": """{% extends "portal/base.html" %}
{% block title %}Book conference{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Book a conference</h1>
<table class="table">
  <thead><tr><th>Teacher</th><th>When</th><th>Location</th><th></th></tr></thead>
  <tbody>
    {% for s in slots %}
    <tr>
      <td>{{ s.teacher.display_name }}</td>
      <td>{{ s.start_at|date:"M j, g:i A" }}</td>
      <td>{{ s.location|default:"—" }}</td>
      <td>
        <form method="post" action="{% url 'portal:conference_book' s.id %}" class="d-flex gap-2">
          {% csrf_token %}
          <select name="student_id" class="form-select form-select-sm" required>
            {% for c in children %}<option value="{{ c.id }}">{{ c.full_name }}</option>{% endfor %}
          </select>
          <button type="submit" class="btn btn-sm btn-primary">Book</button>
        </form>
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted">No open slots.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
""",
    "substitute_login.html": """{% load static %}
<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Substitute login — {{ district_name }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light">
<div class="container py-5"><div class="row justify-content-center"><div class="col-md-5">
  <div class="card shadow"><div class="card-body p-4">
    <h1 class="h4 mb-3">Substitute access</h1>
    <p class="text-muted">Enter the 6-digit code from your teacher.</p>
    <form method="post">{% csrf_token %}
      <input type="text" name="access_code" class="form-control form-control-lg text-center mb-3" maxlength="12" required autofocus>
      <button type="submit" class="btn btn-primary w-100">Continue</button>
    </form>
    <p class="mt-3 mb-0 small text-center"><a href="{% url 'portal:login' %}">Staff login</a></p>
  </div></div>
</div></div></div>
</body></html>
""",
    "substitute_dashboard.html": """{% load static %}
<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Substitute — {{ district_name }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body>
<nav class="navbar navbar-dark bg-primary"><div class="container-fluid">
  <span class="navbar-brand">Substitute mode</span>
  <span class="text-white-50 small">Valid {{ pass_obj.valid_date }}</span>
</div></nav>
<main class="container py-4">
  <h1 class="h4 mb-4">Your sections today</h1>
  <div class="row g-3">
    {% for section in sections %}
    <div class="col-md-4">
      <div class="card h-100"><div class="card-body">
        <h2 class="h5">{{ section.course.code }}</h2>
        <p class="text-muted">{{ section.course.name }}</p>
        <a href="{% url 'portal:section_attendance' section.id %}" class="btn btn-primary btn-sm">Take attendance</a>
        <a href="{% url 'portal:gradebook' section.id %}" class="btn btn-outline-secondary btn-sm">View gradebook</a>
      </div></div>
    </div>
    {% endfor %}
  </div>
</main>
</body></html>
""",
    "substitute_manage.html": """{% extends "portal/base.html" %}
{% block title %}Substitute passes{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Substitute passes</h1>
{% if new_pass %}
<div class="alert alert-success">New code for {{ new_pass.valid_date }}: <strong class="fs-5">{{ new_pass.access_code }}</strong></div>
{% endif %}
<form method="post" class="mb-4 col-lg-8">
  {% csrf_token %}
  <div class="mb-3">
    <label class="form-label">Valid date</label>
    <input type="date" name="valid_date" class="form-control" value="{{ today|default:'' }}">
  </div>
  <div class="mb-3">
    <label class="form-label">Sections</label>
    {% for s in sections %}
    <div class="form-check">
      <input class="form-check-input" type="checkbox" name="section_ids" value="{{ s.id }}" id="sec{{ s.id }}">
      <label class="form-check-label" for="sec{{ s.id }}">{{ s.course.code }} — Section {{ s.section_number }}</label>
    </div>
    {% endfor %}
  </div>
  <button type="submit" class="btn btn-primary">Generate code</button>
</form>
<table class="table table-sm">
  <thead><tr><th>Date</th><th>Code</th><th>Sections</th><th>Active</th></tr></thead>
  <tbody>
    {% for p in passes %}
    <tr>
      <td>{{ p.valid_date }}</td>
      <td><code>{{ p.access_code }}</code></td>
      <td>{% for s in p.sections.all %}{{ s.course.code }} {% endfor %}</td>
      <td>{% if p.is_active %}Yes{% else %}No{% endif %}</td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted">No passes yet.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
""",
    "audit_log.html": """{% extends "portal/base.html" %}
{% block title %}Audit log{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Audit log</h1>
<table class="table table-sm table-striped">
  <thead><tr><th>When</th><th>User</th><th>Action</th><th>Model</th><th>Object</th></tr></thead>
  <tbody>
    {% for log in logs %}
    <tr>
      <td>{{ log.created_at|date:"M j, Y g:i A" }}</td>
      <td>{% if log.user %}{{ log.user.username }}{% else %}—{% endif %}</td>
      <td>{{ log.action }}</td>
      <td>{{ log.model_name }}</td>
      <td>{{ log.object_id }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="5" class="text-muted">No entries.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
""",
    "accommodations.html": """{% extends "portal/base.html" %}
{% block title %}Accommodations{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Accommodations — {{ student.full_name }}</h1>
<ul class="list-group mb-4">
  {% for a in accommodations %}
  <li class="list-group-item">
    <span class="badge bg-info text-dark">{{ a.get_accommodation_type_display }}</span>
    <strong>{{ a.title }}</strong>
    <div class="small text-muted">{{ a.description }}</div>
  </li>
  {% empty %}
  <li class="list-group-item text-muted">No active accommodations.</li>
  {% endfor %}
</ul>
<form method="post" class="col-lg-8">
  {% csrf_token %}
  <div class="row g-2">
    <div class="col-md-3">
      <select name="accommodation_type" class="form-select">
        <option value="iep">IEP</option>
        <option value="504">504 Plan</option>
        <option value="other">Other</option>
      </select>
    </div>
    <div class="col-md-4"><input type="text" name="title" class="form-control" placeholder="Title" required></div>
    <div class="col-md-4"><input type="text" name="description" class="form-control" placeholder="Description"></div>
    <div class="col-md-1"><button type="submit" class="btn btn-primary">Add</button></div>
  </div>
</form>
{% endblock %}
""",
    "posting_windows.html": """{% extends "portal/base.html" %}
{% block title %}Grade posting windows{% endblock %}
{% block content %}
<h1 class="h3 mb-4">Grade posting windows</h1>
<form method="post" class="row g-2 mb-4 col-lg-10">
  {% csrf_token %}
  <div class="col-md-2">
    <select name="term_id" class="form-select" required>
      {% for t in terms %}<option value="{{ t.id }}">{{ t.name }}</option>{% endfor %}
    </select>
  </div>
  <div class="col-md-2"><input type="text" name="name" class="form-control" placeholder="Name" required></div>
  <div class="col-md-3"><input type="datetime-local" name="opens_at" class="form-control" required></div>
  <div class="col-md-3"><input type="datetime-local" name="closes_at" class="form-control" required></div>
  <div class="col-md-2"><button type="submit" class="btn btn-primary w-100">Add window</button></div>
</form>
<table class="table">
  <thead><tr><th>Term</th><th>Name</th><th>Opens</th><th>Closes</th></tr></thead>
  <tbody>
    {% for w in windows %}
    <tr>
      <td>{{ w.term.name }}</td>
      <td>{{ w.name }}</td>
      <td>{{ w.opens_at|date:"M j, Y g:i A" }}</td>
      <td>{{ w.closes_at|date:"M j, Y g:i A" }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted">No posting windows configured (grades publish anytime).</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
""",
}

if __name__ == "__main__":
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    for name, content in FILES.items():
        path = TEMPLATES / name
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")
