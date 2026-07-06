import os
import uuid

from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename


def allowed_profile_file(filename):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_PROFILE_EXTENSIONS"]


def save_profile_picture(user, file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_profile_file(file_storage.filename):
        raise ValueError("Invalid image type. Use PNG, JPG, GIF, or WebP.")

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    folder = current_app.config["PROFILE_UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)

    img = Image.open(file_storage.stream)
    img.thumbnail((512, 512))
    if ext in ("jpg", "jpeg"):
        img = img.convert("RGB")
    img.save(path)

    if user.profile_picture:
        old = os.path.join(current_app.config["UPLOAD_FOLDER"], user.profile_picture)
        if os.path.isfile(old):
            try:
                os.remove(old)
            except OSError:
                pass

    return f"profiles/{filename}"
