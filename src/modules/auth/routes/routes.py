from datetime import datetime, timezone
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from infra.http.authentication import (
    account,
    authenticated,
    claims,
    identity,
    optional_authentication,
)
from infra.http.boundary import json_body
from infra.http.contract import Actions
from infra.http.documentation import documented
from infra.images.contract import PHOTO_LIMIT
from infra.security.tokens.contract import TokenIssuer
from modules.auth.domain.errors import ValidationError


def create_routes(actions: Actions, tokens: TokenIssuer):
    blueprint = Blueprint("auth", __name__)

    @blueprint.post("/auth/login")
    @documented(
        "Autenticação",
        "Entrar",
        response="LoginResult",
        body="LoginInput",
        status=200,
        public=True,
        multipart=False,
    )
    def login():
        data = json_body({"email", "password"})
        user = actions.login.execute(data.get("email"), data.get("password"))
        return jsonify(
            {
                "access_token": tokens.issue(user.id, user.auth_version),
                "user": user.to_public(),
            }
        )

    @blueprint.post("/auth/register")
    @documented(
        "Autenticação",
        "Cadastrar com convite",
        response="User",
        body="RegisterInput",
        status=201,
        public=True,
        multipart=False,
    )
    def register():
        return jsonify(actions.register.execute(json_body())), 201

    @blueprint.post("/auth/logout")
    @documented(
        "Autenticação",
        "Encerrar sessão",
        response=None,
        body=None,
        status=204,
        public=False,
        multipart=False,
    )
    @authenticated
    def logout():
        payload = claims()
        actions.logout.execute(
            payload["jti"], datetime.fromtimestamp(payload["exp"], timezone.utc)
        )
        return "", 204

    @blueprint.get("/auth/me")
    @documented(
        "Autenticação",
        "Consultar identidade",
        response="User",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def me():
        return jsonify(actions.getCurrentUser.execute(account()))

    @blueprint.post("/invitations")
    @documented(
        "Convites",
        "Enviar convite ou iniciar bootstrap",
        response="Invitation",
        body="InvitationInput",
        status=201,
        public=True,
        multipart=False,
    )
    @optional_authentication
    def invite():
        data = json_body({"email"})
        return jsonify(
            actions.issueInvitation.execute(
                data.get("email"), identity(), request.headers.get("X-Bootstrap-Key")
            )
        ), 201

    @blueprint.get("/profiles/options")
    @documented(
        "Perfis",
        "Consultar opções de perfil",
        response="ProfileOptions",
        body=None,
        status=200,
        public=True,
        multipart=False,
    )
    def profile_options():
        return jsonify(actions.getProfileOptions.execute())

    @blueprint.get("/profiles/me")
    @documented(
        "Perfis",
        "Consultar próprio perfil",
        response="Profile",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def own_profile():
        return jsonify(actions.getProfile.execute(identity()))

    @blueprint.patch("/profiles/me")
    @documented(
        "Perfis",
        "Editar próprio perfil",
        response="Profile",
        body="ProfileUpdate",
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def update_profile():
        return jsonify(actions.updateProfile.execute(identity(), json_body()))

    @blueprint.get("/profiles/<identifier>")
    @documented(
        "Perfis",
        "Consultar perfil ativo",
        response="Profile",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def profile(identifier):
        return jsonify(actions.getProfile.execute(identifier))

    @blueprint.get("/entities")
    @documented(
        "Entidades",
        "Listar entidades",
        response="Entities",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def entities():
        return jsonify(actions.listEntities.execute())

    @blueprint.get("/research-projects")
    @documented(
        "Pesquisas",
        "Listar pesquisas",
        response="Projects",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def projects():
        return jsonify(actions.listResearchProjects.execute())

    @blueprint.post("/research-projects")
    @documented(
        "Pesquisas",
        "Criar pesquisa e vincular ao perfil",
        response="Project",
        body="ProjectInput",
        status=201,
        public=False,
        multipart=False,
    )
    @authenticated
    def create_project():
        return jsonify(
            actions.createResearchProject.execute(identity(), json_body())
        ), 201

    @blueprint.get("/research-projects/<identifier>")
    @documented(
        "Pesquisas",
        "Consultar pesquisa",
        response="Project",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def project(identifier):
        return jsonify(actions.getResearchProject.execute(identifier))

    @blueprint.patch("/research-projects/<identifier>")
    @documented(
        "Pesquisas",
        "Editar pesquisa própria",
        response="Project",
        body="ProjectUpdate",
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def update_project(identifier):
        return jsonify(
            actions.updateResearchProject.execute(identity(), identifier, json_body())
        )

    @blueprint.get("/research-participations")
    @documented(
        "Orientações",
        "Listar orientações recebidas",
        response="Participations",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def participations():
        return jsonify(
            actions.listResearchParticipations.execute(
                identity(), request.args.get("status", "pending")
            )
        )

    @blueprint.patch("/research-participations/<identifier>")
    @documented(
        "Orientações",
        "Confirmar ou rejeitar orientação",
        response=None,
        body="ReviewInput",
        status=204,
        public=False,
        multipart=False,
    )
    @authenticated
    def review_participation(identifier):
        actions.reviewResearchParticipation.execute(identity(), identifier, json_body())
        return "", 204

    @blueprint.patch("/account/email")
    @documented(
        "Conta",
        "Alterar email",
        response=None,
        body="EmailInput",
        status=204,
        public=False,
        multipart=False,
    )
    @authenticated
    def change_email():
        actions.changeEmail.execute(account(), json_body())
        return "", 204

    @blueprint.patch("/account/password")
    @documented(
        "Conta",
        "Alterar password",
        response=None,
        body="PasswordInput",
        status=204,
        public=False,
        multipart=False,
    )
    @authenticated
    def change_password():
        actions.changePassword.execute(account(), json_body())
        return "", 204

    @blueprint.delete("/account")
    @documented(
        "Conta",
        "Excluir própria conta",
        response=None,
        body="CurrentPasswordInput",
        status=204,
        public=False,
        multipart=False,
    )
    @authenticated
    def delete_account():
        actions.deleteAccount.execute(account(), json_body())
        return "", 204

    @blueprint.get("/profiles/me/photo")
    @documented(
        "Fotos",
        "Obter própria foto",
        response=None,
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def own_photo():
        photo_id, content = actions.getPhoto.execute(identity())
        response = send_file(
            BytesIO(content),
            mimetype="image/png",
            download_name="profile.png",
            etag=photo_id,
            max_age=300,
        )
        response.headers["Cache-Control"] = "private, max-age=300"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response.make_conditional(request)

    @blueprint.get("/profiles/<identifier>/photo")
    @documented(
        "Fotos",
        "Obter foto de perfil ativo",
        response=None,
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def photo(identifier):
        photo_id, content = actions.getPhoto.execute(identifier)
        response = send_file(
            BytesIO(content),
            mimetype="image/png",
            download_name="profile.png",
            etag=photo_id,
            max_age=300,
        )
        response.headers["Cache-Control"] = "private, max-age=300"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response.make_conditional(request)

    @blueprint.put("/profiles/me/photo")
    @documented(
        "Fotos",
        "Enviar JPEG/PNG de até 2 MiB",
        response=None,
        body="PhotoInput",
        status=204,
        public=False,
        multipart=True,
    )
    @authenticated
    def upload_photo():
        request.max_content_length = PHOTO_LIMIT + 64 * 1024
        upload = request.files.get("photo")
        if (
            upload is None
            or set(request.files) != {"photo"}
            or len(request.files.getlist("photo")) != 1
            or request.form
        ):
            raise ValidationError("Envie uma imagem no campo photo")
        actions.uploadPhoto.execute(identity(), upload.stream.read(PHOTO_LIMIT + 1))
        return "", 204

    @blueprint.delete("/profiles/me/photo")
    @documented(
        "Fotos",
        "Remover própria foto",
        response=None,
        body=None,
        status=204,
        public=False,
        multipart=False,
    )
    @authenticated
    def delete_photo():
        actions.deletePhoto.execute(identity())
        return "", 204

    return blueprint
