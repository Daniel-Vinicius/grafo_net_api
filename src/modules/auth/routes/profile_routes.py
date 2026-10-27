from io import BytesIO

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import current_user, get_current_user, jwt_required

from modules.auth.domain.errors import NotFoundError, PayloadTooLargeError, ValidationError
from modules.auth.domain.profile import COURSES, FIELDS, STATUSES
from modules.auth.repositories.contract import PhotoStore, ProfileRepository
from modules.auth.useCases.profile.profile import PHOTO_LIMIT, ProfileUseCase


def register_profile_routes(blueprint: Blueprint, repository: ProfileRepository, photos: PhotoStore) -> None:
    service = ProfileUseCase(repository, photos)

    def body() -> dict:
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise ValidationError("Envie um objeto JSON válido")
        return value

    @blueprint.get("/auth/profile-options")
    def options():
        return jsonify({"courses": COURSES, "fields": FIELDS, "semesters": list(range(1, 9)), "statuses": STATUSES})

    @blueprint.get("/auth/profile")
    @jwt_required()
    def own_profile():
        return jsonify(service.get(current_user.id).to_public())

    @blueprint.patch("/auth/profile")
    @jwt_required()
    def edit_profile():
        return jsonify(service.update(current_user.id, body()).to_public())

    @blueprint.get("/auth/entities")
    @jwt_required()
    def entities():
        return jsonify(repository.list_entities())

    @blueprint.get("/auth/research-projects")
    @jwt_required()
    def projects():
        return jsonify([project.to_public() for project in repository.list_projects()])

    @blueprint.post("/auth/research-projects")
    @jwt_required()
    def create_project():
        return jsonify(service.create_project(current_user.id, body()).to_public()), 201

    @blueprint.get("/auth/research-projects/<project_id>")
    @jwt_required()
    def project(project_id: str):
        return jsonify(service.get_project(project_id).to_public())

    @blueprint.patch("/auth/research-projects/<project_id>")
    @jwt_required()
    def edit_project(project_id: str):
        return jsonify(service.update_project(current_user.id, project_id, body()).to_public())

    @blueprint.patch("/auth/account/email")
    @jwt_required()
    def email():
        service.change_email(get_current_user(), body())
        return "", 204

    @blueprint.patch("/auth/account/password")
    @jwt_required()
    def password():
        service.change_password(get_current_user(), body())
        return "", 204

    @blueprint.delete("/auth/account")
    @jwt_required()
    def delete_account():
        service.delete(get_current_user(), body())
        return "", 204

    @blueprint.put("/auth/profile/photo")
    @jwt_required()
    def upload_photo():
        # Limita também o envelope multipart antes de o parser carregar o arquivo.
        request.max_content_length = PHOTO_LIMIT + 64 * 1024
        upload = request.files.get("photo")
        if upload is None or set(request.files) != {"photo"} or len(request.files.getlist("photo")) != 1 or request.form:
            raise ValidationError("Envie uma única imagem no campo photo")
        content = upload.stream.read(PHOTO_LIMIT + 1)
        if len(content) > PHOTO_LIMIT:
            raise PayloadTooLargeError("Foto deve ter até 2 MiB")
        service.upload_photo(current_user.id, content)
        return "", 204

    @blueprint.get("/auth/profile/photo")
    @jwt_required()
    def photo():
        profile = service.get(current_user.id)
        content = photos.get(profile.photo_id) if profile.photo_id else None
        if content is None:
            raise NotFoundError("Foto não encontrada")
        response = send_file(BytesIO(content), mimetype="image/png", download_name="profile.png", max_age=0)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @blueprint.delete("/auth/profile/photo")
    @jwt_required()
    def delete_photo():
        service.remove_photo(current_user.id)
        return "", 204
