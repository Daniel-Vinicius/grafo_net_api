import click

from infra.database.seed import seed_development
from infra.database.setup import prepare_database, reset_development_data
from infra.security.passwords.bcrypt import BcryptPasswordHasher


def register_commands(app, application):
    @app.cli.command("prepare-db")
    def prepare():
        prepare_database(application.database)
        click.echo("Coleções, validadores, índices e entidades preparados")

    @app.cli.command("reset-dev-data")
    def reset():
        reset_development_data(application.database)
        click.echo("Dados removidos e catálogos repostos")

    @app.cli.command("seed-dev")
    def seed():
        count = seed_development(application, BcryptPasswordHasher())
        click.echo(f"{count} contas criadas; seed concluído")

    @app.cli.command("cleanup-photos")
    def cleanup():
        click.echo(f"Fotos removidas: {application.actions.cleanupPhotos.execute()}")

    @app.cli.command("reindex-profiles")
    @click.option("--user-id")
    @click.option("--entity-id")
    @click.option("--project-id")
    @click.option("--force", is_flag=True)
    def reindex(user_id, entity_id, project_id, force):
        if sum(bool(value) for value in (user_id, entity_id, project_id)) > 1:
            raise click.UsageError("Use somente um seletor")
        reference = (
            ("entity", entity_id)
            if entity_id
            else (("project", project_id) if project_id else None)
        )
        counts = application.actions.indexProfiles.execute(
            user_id=user_id, reference=reference, force=force
        )
        click.echo(
            f"Indexados: {counts['indexed']}; atuais: {counts['unchanged']}; pendentes: {counts['pending']}"
        )
        if counts["pending"]:
            raise click.ClickException("Há perfis pendentes; repita a indexação")
