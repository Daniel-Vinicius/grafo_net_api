from dataclasses import asdict
from io import BytesIO
import warnings
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from pymongo.errors import PyMongoError

from modules.auth.domain.errors import AuthenticationRequiredError, ForbiddenError, NotFoundError, PayloadTooLargeError, ValidationError
from modules.auth.domain.invite import normalize_email
from modules.auth.domain.profile import Profile, ResearchProject, identifiers
from modules.auth.domain.user import User
from modules.auth.passwords import check_password, hash_password
from modules.auth.repositories.contract import PhotoStore, ProfileRepository

PHOTO_LIMIT = 2 * 1024 * 1024


def clean_photos(repository: ProfileRepository, photos: PhotoStore) -> int:
    cleaned = 0
    try:
        pending = repository.pending_photos()
    except PyMongoError:
        return 0
    for photo_id in pending:
        try:
            if repository.photo_referenced(photo_id):
                continue
            photos.delete(photo_id)
            repository.finish_photo_cleanup(photo_id)
            cleaned += 1
        except (PyMongoError, OSError):
            # O item permanece na fila para a próxima execução do comando.
            continue
    return cleaned


class ProfileUseCase:
    def __init__(self, repository: ProfileRepository, photos: PhotoStore):
        self.repository = repository
        self.photos = photos

    def get(self, user_id: str) -> Profile:
        profile = self.repository.get_profile(user_id)
        if profile is None:
            raise NotFoundError("Perfil não encontrado")
        return profile

    def update(self, user_id: str, data: dict) -> Profile:
        basic = {"name", "course_id", "semester", "field_id", "bio"}
        extra = {"entity_ids", "research_project_ids", "experiences_completed"}
        if set(data) - basic - extra:
            raise ValidationError("Campo de perfil inválido")
        existing = asdict(self.get(user_id))
        values = {key: data.get(key, existing[key]) for key in basic}
        validated = asdict(Profile.create(user_id, values))
        changes = {key: validated[key] for key in data.keys() & basic}
        for key in ("entity_ids", "research_project_ids"):
            if key in data:
                changes[key] = identifiers(data[key])
        if "experiences_completed" in data:
            if type(data["experiences_completed"]) is not bool:
                raise ValidationError("Conclusão das experiências deve ser booleana")
            changes["experiences_completed"] = data["experiences_completed"]
        return self.repository.patch_profile(user_id, changes)

    def create_project(self, user_id: str, data: dict) -> ResearchProject:
        project = ResearchProject.create(user_id, data)
        self.repository.create_project(user_id, project)
        return project

    def get_project(self, project_id: str) -> ResearchProject:
        project = self.repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Pesquisa não encontrada")
        return project

    def update_project(self, user_id: str, project_id: str, data: dict) -> ResearchProject:
        project = self.get_project(project_id)
        if project.creator_id != user_id:
            raise ForbiddenError("Somente o criador pode editar a pesquisa")
        values = asdict(project)
        del values["id"]
        del values["creator_id"]
        if set(data) - values.keys():
            raise ValidationError("Campo de pesquisa inválido")
        values.update(data)
        updated = ResearchProject.create(user_id, values, project_id)
        self.repository.update_project(user_id, updated)
        return updated

    @staticmethod
    def current_password(user: User, value: object) -> None:
        if not isinstance(value, str) or not check_password(value, user.password_hash):
            raise AuthenticationRequiredError("Senha atual incorreta")

    def change_email(self, user: User, data: dict) -> None:
        if set(data) != {"current_password", "new_email"}:
            raise ValidationError("Informe senha atual e novo e-mail")
        self.current_password(user, data.get("current_password"))
        email = normalize_email(data.get("new_email"))
        if email == user.email:
            raise ValidationError("Informe um e-mail diferente do atual")
        self.repository.change_credentials(user, {"email": email})

    def change_password(self, user: User, data: dict) -> None:
        if set(data) != {"current_password", "new_password"}:
            raise ValidationError("Informe senha atual e nova senha")
        self.current_password(user, data.get("current_password"))
        password = data.get("new_password")
        if not isinstance(password, str) or len(password) < 8 or len(password.encode("utf-8")) > 72:
            raise ValidationError("Senha deve ter pelo menos 8 caracteres e no máximo 72 bytes UTF-8")
        if check_password(password, user.password_hash):
            raise ValidationError("Informe uma senha diferente da atual")
        self.repository.change_credentials(user, {"password_hash": hash_password(password)})

    def delete(self, user: User, data: dict) -> None:
        if set(data) != {"current_password"}:
            raise ValidationError("Informe somente a senha atual")
        self.current_password(user, data.get("current_password"))
        self.repository.delete_account(user)
        clean_photos(self.repository, self.photos)

    def upload_photo(self, user_id: str, content: bytes) -> None:
        self.get(user_id)
        if len(content) > PHOTO_LIMIT:
            raise PayloadTooLargeError("Foto deve ter até 2 MiB")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as original:
                    if original.format not in {"JPEG", "PNG"} or original.width * original.height > 16_000_000:
                        raise ValidationError("Use JPEG ou PNG com até 16 milhões de pixels")
                    original.load()
                    image = ImageOps.exif_transpose(original).convert("RGBA")
                    image.thumbnail((512, 512))
                    # Nova imagem elimina EXIF e metadados não relacionados aos pixels.
                    clean = Image.new("RGBA", image.size)
                    clean.paste(image)
                    output = BytesIO()
                    clean.save(output, format="PNG")
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise ValidationError("Imagem inválida") from None
        photo_id = str(uuid4())
        self.repository.queue_photo(photo_id, delayed=True)
        try:
            self.photos.put(photo_id, output.getvalue())
            self.repository.set_photo(user_id, photo_id)
        except Exception:
            self.repository.queue_photo(photo_id)
            clean_photos(self.repository, self.photos)
            raise
        clean_photos(self.repository, self.photos)

    def remove_photo(self, user_id: str) -> None:
        self.get(user_id)
        self.repository.set_photo(user_id, None)
        clean_photos(self.repository, self.photos)
