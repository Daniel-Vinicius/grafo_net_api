from dataclasses import dataclass

from modules.auth.repositories.entities.contract import EntityRepository
from modules.auth.repositories.invites.contract import InviteRepository
from modules.auth.repositories.photoCleanup.contract import PhotoCleanupRepository
from modules.auth.repositories.photos.contract import PhotoRepository
from modules.auth.repositories.profiles.contract import ProfileRepository
from modules.auth.repositories.researchProjects.contract import (
    ResearchProjectRepository,
)
from modules.auth.repositories.tokens.contract import TokenRepository
from modules.auth.repositories.users.contract import UserRepository
from modules.connections.repositories.connections.contract import ConnectionRepository
from modules.graph.repositories.networkProfiles.contract import NetworkProfileRepository
from modules.search.repositories.embeddings.contract import EmbeddingRepository


@dataclass
class Repositories:
    users: UserRepository
    tokens: TokenRepository
    invites: InviteRepository
    profiles: ProfileRepository
    entities: EntityRepository
    projects: ResearchProjectRepository
    photos: PhotoRepository
    cleanup: PhotoCleanupRepository
    connections: ConnectionRepository
    embeddings: EmbeddingRepository
    network: NetworkProfileRepository
