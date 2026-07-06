# LibreGrades Celery beat scheduler (Windows — run in a separate terminal from the worker)
Set-Location $PSScriptRoot\..
& .\.venv\Scripts\Activate.ps1
celery -A config beat -l info
