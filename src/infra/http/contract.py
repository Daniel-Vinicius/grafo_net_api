from dataclasses import dataclass

from modules.auth.useCases.changeEmail.changeEmailUseCase import ChangeEmailUseCase
from modules.auth.useCases.changePassword.changePasswordUseCase import (
    ChangePasswordUseCase,
)
from modules.auth.useCases.cleanupPhotos.cleanupPhotosUseCase import (
    CleanupPhotosUseCase,
)
from modules.auth.useCases.createResearchProject.createResearchProjectUseCase import (
    CreateResearchProjectUseCase,
)
from modules.auth.useCases.deleteAccount.deleteAccountUseCase import (
    DeleteAccountUseCase,
)
from modules.auth.useCases.deletePhoto.deletePhotoUseCase import DeletePhotoUseCase
from modules.auth.useCases.getCurrentUser.getCurrentUserUseCase import (
    GetCurrentUserUseCase,
)
from modules.auth.useCases.getPhoto.getPhotoUseCase import GetPhotoUseCase
from modules.auth.useCases.getProfile.getProfileUseCase import GetProfileUseCase
from modules.auth.useCases.getProfileOptions.getProfileOptionsUseCase import (
    GetProfileOptionsUseCase,
)
from modules.auth.useCases.getResearchProject.getResearchProjectUseCase import (
    GetResearchProjectUseCase,
)
from modules.auth.useCases.issueInvitation.issueInvitationUseCase import (
    IssueInvitationUseCase,
)
from modules.auth.useCases.listEntities.listEntitiesUseCase import ListEntitiesUseCase
from modules.auth.useCases.listResearchParticipations.listResearchParticipationsUseCase import (
    ListResearchParticipationsUseCase,
)
from modules.auth.useCases.listResearchProjects.listResearchProjectsUseCase import (
    ListResearchProjectsUseCase,
)
from modules.auth.useCases.login.loginUseCase import LoginUseCase
from modules.auth.useCases.logout.logoutUseCase import LogoutUseCase
from modules.auth.useCases.register.registerUseCase import RegisterUseCase
from modules.auth.useCases.reviewResearchParticipation.reviewResearchParticipationUseCase import (
    ReviewResearchParticipationUseCase,
)
from modules.auth.useCases.updateProfile.updateProfileUseCase import (
    UpdateProfileUseCase,
)
from modules.auth.useCases.updateResearchProject.updateResearchProjectUseCase import (
    UpdateResearchProjectUseCase,
)
from modules.auth.useCases.uploadPhoto.uploadPhotoUseCase import UploadPhotoUseCase
from modules.connections.useCases.acceptConnection.acceptConnectionUseCase import (
    AcceptConnectionUseCase,
)
from modules.connections.useCases.listConnections.listConnectionsUseCase import (
    ListConnectionsUseCase,
)
from modules.connections.useCases.removeConnection.removeConnectionUseCase import (
    RemoveConnectionUseCase,
)
from modules.connections.useCases.requestConnection.requestConnectionUseCase import (
    RequestConnectionUseCase,
)
from modules.graph.useCases.buildGraph.buildGraphUseCase import BuildGraphUseCase
from modules.graph.useCases.getCloseNetwork.getCloseNetworkUseCase import (
    GetCloseNetworkUseCase,
)
from modules.graph.useCases.getNetworkStats.getNetworkStatsUseCase import (
    GetNetworkStatsUseCase,
)
from modules.graph.useCases.getPath.getPathUseCase import GetPathUseCase
from modules.search.useCases.indexProfiles.indexProfilesUseCase import (
    IndexProfilesUseCase,
)
from modules.search.useCases.searchProfiles.searchProfilesUseCase import (
    SearchProfilesUseCase,
)


@dataclass
class Actions:
    login: LoginUseCase
    logout: LogoutUseCase
    getCurrentUser: GetCurrentUserUseCase
    register: RegisterUseCase
    issueInvitation: IssueInvitationUseCase
    getProfileOptions: GetProfileOptionsUseCase
    getProfile: GetProfileUseCase
    updateProfile: UpdateProfileUseCase
    listEntities: ListEntitiesUseCase
    listResearchProjects: ListResearchProjectsUseCase
    getResearchProject: GetResearchProjectUseCase
    createResearchProject: CreateResearchProjectUseCase
    updateResearchProject: UpdateResearchProjectUseCase
    changeEmail: ChangeEmailUseCase
    changePassword: ChangePasswordUseCase
    deleteAccount: DeleteAccountUseCase
    cleanupPhotos: CleanupPhotosUseCase
    getPhoto: GetPhotoUseCase
    uploadPhoto: UploadPhotoUseCase
    deletePhoto: DeletePhotoUseCase
    listResearchParticipations: ListResearchParticipationsUseCase
    reviewResearchParticipation: ReviewResearchParticipationUseCase
    listConnections: ListConnectionsUseCase
    requestConnection: RequestConnectionUseCase
    acceptConnection: AcceptConnectionUseCase
    removeConnection: RemoveConnectionUseCase
    buildGraph: BuildGraphUseCase
    getCloseNetwork: GetCloseNetworkUseCase
    getNetworkStats: GetNetworkStatsUseCase
    getPath: GetPathUseCase
    indexProfiles: IndexProfilesUseCase
    searchProfiles: SearchProfilesUseCase
