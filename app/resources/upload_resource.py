import mimetypes, os
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from flask_smorest import Blueprint
from botocore.exceptions import ClientError

from ..ext.s3 import s3_client, s3_key_for_cv, public_url_from_key, AWS_BUCKET

blp = Blueprint("Uploads", __name__, description="Carga de CVs a S3")

@blp.route("/cv", methods=["POST"])
@jwt_required()
def upload_cv():
    if not AWS_BUCKET:
        return jsonify({"message": "Config error: AWS_BUCKET no seteado"}), 500

    if "cv" not in request.files:
        return jsonify({"message": "No se envió archivo en el campo 'cv'"}), 400

    f = request.files["cv"]
    filename = secure_filename(f.filename or "")
    if not filename.lower().endswith(".pdf"):
        return jsonify({"message": "El CV debe ser un PDF"}), 400

    # límite 25MB
    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    if size > 25 * 1024 * 1024:
        return jsonify({"message": "El CV no debe superar 5MB"}), 400

    applicant_id = int(get_jwt_identity())
    try:
        vacancy_id = int(request.form.get("vacancy_id") or 0)
    except ValueError:
        vacancy_id = 0

    key = s3_key_for_cv(vacancy_id or 0, applicant_id, filename)
    content_type = mimetypes.guess_type(filename)[0] or "application/pdf"

    try:
        s3_client.upload_fileobj(
            f,
            AWS_BUCKET,
            key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "max-age=31536000, public",
            },
        )
    except ClientError as e:
        current_app.logger.exception("S3 upload error")
        err = e.response.get("Error", {})
        return jsonify({
            "message": "No se pudo subir el CV",
            "code": err.get("Code"),
            "error": err.get("Message"),
        }), 500
    except Exception as e:
        current_app.logger.exception("Error subiendo CV a S3")
        return jsonify({"message": "No se pudo subir el CV", "error": str(e)}), 500

    return jsonify({"key": key, "url": public_url_from_key(key)}), 201
