from modules.auth.domain.profile import Profile


def make_profile(identifier, name, **metadata):
    return Profile(
        identifier,
        name,
        **{
            "course_id": "computer-science",
            "semester": 1,
            "field_id": "technology",
            "bio": "Bio",
            **metadata,
        },
    )
