import logging

from infra.errors import UnavailableError


def notify_index(index, **selector):
    try:
        index.execute(**selector)
    except UnavailableError:
        logging.getLogger(__name__).warning(
            "Indexação pendente; repetir reindex-profiles"
        )
