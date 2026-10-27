import click
from flask import Flask

from modules.search.useCases.index.index import IndexProfilesUseCase


def register_search_commands(app: Flask, index: IndexProfilesUseCase) -> None:
    @app.cli.command("reindex-profiles")
    @click.option("--user-id", help="Atualiza somente este usuário.")
    @click.option("--force", is_flag=True, help="Reconstrói mesmo os vetores atuais.")
    @click.option("--entity-id", help="Atualiza os participantes desta entidade.")
    @click.option("--project-id", help="Atualiza os participantes deste projeto.")
    def reindex(user_id: str | None, force: bool, entity_id: str | None, project_id: str | None):
        if sum(bool(value) for value in (user_id, entity_id, project_id)) > 1:
            raise click.UsageError("Use somente um seletor por execução")
        reference = ("entity", entity_id) if entity_id else (("project", project_id) if project_id else None)
        counts = index.refresh(user_id=user_id, force=force, reference=reference)
        click.echo(f"Indexados: {counts['indexed']}; atuais: {counts['unchanged']}; pendentes: {counts['pending']}")
        if counts["pending"]:
            raise click.ClickException("Há perfis pendentes; confira a configuração/cota do Gemini e execute novamente")
