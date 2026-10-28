from infra.database.context import Repositories
from modules.auth.repositories.entities.in_memory.repository import (
    InMemoryEntityRepository,
)
from modules.auth.repositories.entities.mongo.repository import MongoEntityRepository
from modules.auth.repositories.invites.in_memory.repository import (
    InMemoryInviteRepository,
)
from modules.auth.repositories.invites.mongo.repository import MongoInviteRepository
from modules.auth.repositories.photoCleanup.in_memory.repository import (
    InMemoryPhotoCleanupRepository,
)
from modules.auth.repositories.photoCleanup.mongo.repository import (
    MongoPhotoCleanupRepository,
)
from modules.auth.repositories.photos.in_memory.repository import (
    InMemoryPhotoRepository,
)
from modules.auth.repositories.photos.mongo.repository import MongoPhotoRepository
from modules.auth.repositories.profiles.in_memory.repository import (
    InMemoryProfileRepository,
)
from modules.auth.repositories.profiles.mongo.repository import MongoProfileRepository
from modules.auth.repositories.researchProjects.in_memory.repository import (
    InMemoryResearchProjectRepository,
)
from modules.auth.repositories.researchProjects.mongo.repository import (
    MongoResearchProjectRepository,
)
from modules.auth.repositories.tokens.in_memory.repository import (
    InMemoryTokenRepository,
)
from modules.auth.repositories.tokens.mongo.repository import MongoTokenRepository
from modules.auth.repositories.users.in_memory.repository import InMemoryUserRepository
from modules.auth.repositories.users.mongo.repository import MongoUserRepository
from modules.connections.repositories.connections.in_memory.repository import (
    InMemoryConnectionRepository,
)
from modules.connections.repositories.connections.mongo.repository import (
    MongoConnectionRepository,
)
from modules.graph.repositories.networkProfiles.in_memory.repository import (
    InMemoryNetworkProfileRepository,
)
from modules.graph.repositories.networkProfiles.mongo.repository import (
    MongoNetworkProfileRepository,
)
from modules.search.repositories.embeddings.in_memory.repository import (
    InMemoryEmbeddingRepository,
)
from modules.search.repositories.embeddings.mongo.repository import (
    MongoEmbeddingRepository,
)


def mongo_repositories(database, session=None):
    return Repositories(
        users=MongoUserRepository(database, session),
        tokens=MongoTokenRepository(database, session),
        invites=MongoInviteRepository(database, session),
        profiles=MongoProfileRepository(database, session),
        entities=MongoEntityRepository(database, session),
        projects=MongoResearchProjectRepository(database, session),
        cleanup=MongoPhotoCleanupRepository(database, session),
        photos=MongoPhotoRepository(database, session),
        connections=MongoConnectionRepository(database, session),
        embeddings=MongoEmbeddingRepository(database, session),
        network=MongoNetworkProfileRepository(database, session),
    )


def memory_repositories(database):
    return Repositories(
        users=InMemoryUserRepository(database),
        tokens=InMemoryTokenRepository(database),
        invites=InMemoryInviteRepository(database),
        profiles=InMemoryProfileRepository(database),
        entities=InMemoryEntityRepository(database),
        projects=InMemoryResearchProjectRepository(database),
        cleanup=InMemoryPhotoCleanupRepository(database),
        photos=InMemoryPhotoRepository(database),
        connections=InMemoryConnectionRepository(database),
        embeddings=InMemoryEmbeddingRepository(database),
        network=InMemoryNetworkProfileRepository(database),
    )
