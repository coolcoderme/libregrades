# LibreGrades Celery worker (Windows — run beat separately; see start_celery_beat.ps1)
Set-Location $PSScriptRoot\..
& .\.venv\Scripts\Activate.ps1
celery -A config worker -l info -P solo
