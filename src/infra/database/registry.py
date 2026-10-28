from modules.auth.repositories.entities.mongo import schema as entities
from modules.auth.repositories.invites.mongo import schema as invites
from modules.auth.repositories.photoCleanup.mongo import schema as cleanup
from modules.auth.repositories.profiles.mongo import schema as profiles
from modules.auth.repositories.researchProjects.mongo import schema as projects
from modules.auth.repositories.tokens.mongo import schema as tokens
from modules.auth.repositories.users.mongo import schema as users
from modules.connections.repositories.connections.mongo import schema as connections
from modules.search.repositories.embeddings.mongo import schema as embeddings

SCHEMAS = {
    "users": users,
    "revoked_tokens": tokens,
    "invites": invites,
    "profiles": profiles,
    "entities": entities,
    "research_projects": projects,
    "photo_cleanup": cleanup,
    "connections": connections,
    "profile_embeddings": embeddings,
}
COLLECTIONS = (*SCHEMAS, "profile_photos.files", "profile_photos.chunks")
