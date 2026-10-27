"""Integração para auth e para o futuro endpoint de edição de perfil."""

from flask import Flask


def profile_saved(app: Flask, user_id: str) -> None:
    callback = app.extensions.get("profile_saved")
    if callback is None:
        return
    try:
        callback(user_id=user_id)
    except Exception:
        # A conta/perfil já foi salvo. A busca rejeita hashes antigos e o CLI
        # recupera índices ausentes/pendentes; nunca desfazer o perfil por isso.
        app.logger.warning("Indexação pendente após salvar o perfil %s", user_id)
