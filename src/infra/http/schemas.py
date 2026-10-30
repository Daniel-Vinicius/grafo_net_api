from copy import deepcopy


def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def string(maximum=None, nullable=False):
    return {
        "type": "string",
        **({"maxLength": maximum} if maximum else {}),
        **({"nullable": True} if nullable else {}),
    }


def obj(properties, required=()):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        **({"required": list(required)} if required else {}),
    }


def array(item):
    return {"type": "array", "items": item}


def schemas():
    date = {"type": "string", "format": "date"}
    end = {**date, "nullable": True}
    experience = {
        "id": string(),
        "title": string(150),
        "organization": string(150),
        "type": string(100),
        "start_date": date,
        "end_date": end,
        "description": string(2000),
    }
    membership = {
        "id": string(),
        "entity_id": string(),
        "role": string(100),
        "start_date": date,
        "end_date": end,
    }
    participation = {
        "id": string(),
        "project_id": string(),
        "advisor_user_id": string(nullable=True),
        "role": string(100),
        "start_date": date,
        "end_date": end,
        "status": {
            "type": "string",
            "enum": ["pending", "confirmed", "rejected"],
            "readOnly": True,
        },
    }
    field_ids = ["finance", "technology", "entrepreneurship", "cybersecurity"]
    basic = {
        "name": {**string(100), "minLength": 1},
        "course_id": {
            "type": "string",
            "enum": [
                "administration",
                "computer-science",
                "law",
                "economics",
                "computer-engineering",
                "production-engineering",
                "mechanical-engineering",
                "mechatronic-engineering",
            ],
        },
        "semester": {"type": "integer", "minimum": 1, "maximum": 10},
        "field_id": {"type": "string", "enum": ["", *field_ids]},
        "bio": string(500),
    }
    metadata = {
        "entity_ids": array(string()),
        "research_project_ids": array(string()),
        "experiences_completed": {"type": "boolean"},
        "type": {"type": "string", "enum": ["", "aluno", "alumni", "professor"]},
        "entry_year": {
            "type": "integer",
            "minimum": 1900,
            "maximum": 2200,
            "nullable": True,
        },
        "entry_semester": {"type": "integer", "enum": [1, 2, None], "nullable": True},
        "class_group": string(150),
        "role": string(150),
        "company": string(150),
        "experiences": array(ref("ExperienceInput")),
        "entity_memberships": array(ref("MembershipInput")),
        "research_participations": array(ref("ParticipationInput")),
    }
    project = {
        "title": {**string(150), "minLength": 1},
        "description": {**string(2000), "minLength": 1},
        "advisor": {**string(100), "minLength": 1},
        "field_id": {"type": "string", "enum": field_ids},
        "start_date": date,
        "end_date": end,
        "status": {
            "type": "string",
            "enum": ["planned", "in_progress", "completed", "cancelled"],
        },
    }
    cost = obj(
        {
            "contextual_edges": {"type": "integer", "minimum": 0},
            "hops": {"type": "integer", "minimum": 0},
        },
        ("contextual_edges", "hops"),
    )
    path = obj(
        {
            "user_ids": array(string()),
            "steps": array(
                obj(
                    {
                        "edge_id": string(),
                        "order": {"type": "integer"},
                        "source": string(),
                        "target": string(),
                    },
                    ("edge_id", "order", "source", "target"),
                )
            ),
            "cost": cost,
        },
        ("user_ids", "steps", "cost"),
    )
    path["nullable"] = True
    user = obj(
        {"id": string(), "email": {"type": "string", "format": "email"}},
        ("id", "email"),
    )
    option = obj({"id": string(), "name": string()}, ("id", "name"))
    course_option = obj(
        {"id": string(), "name": string(), "semesters": {"type": "integer"}},
        ("id", "name", "semesters"),
    )
    model = {
        "Error": obj({"message": string()}, ("message",)),
        "Health": obj({"status": {"type": "string", "enum": ["ok"]}}, ("status",)),
        "User": user,
        "LoginInput": obj(
            {"email": string(), "password": string()}, ("email", "password")
        ),
        "LoginResult": obj(
            {"access_token": string(), "user": ref("User")}, ("access_token", "user")
        ),
        "RegisterInput": obj(
            {
                "profile": ref("ProfileInput"),
                "email": string(),
                "password": {
                    **string(),
                    "minLength": 8,
                    "description": "Até 72 bytes UTF-8",
                },
                "invite_token": string(),
            },
            ("profile", "email", "password", "invite_token"),
        ),
        "InvitationInput": obj({"email": string()}, ("email",)),
        "Invitation": obj(
            {
                "id": string(),
                "email": string(),
                "expires_at": {"type": "string", "format": "date-time"},
            },
            ("id", "email", "expires_at"),
        ),
        "ExperienceInput": obj(
            experience, tuple(key for key in experience if key != "id")
        ),
        "MembershipInput": obj(
            membership, tuple(key for key in membership if key != "id")
        ),
        "ParticipationInput": obj(
            {key: value for key, value in participation.items() if key != "status"},
            tuple(key for key in participation if key not in ("id", "status")),
        ),
        "Experience": obj(experience, experience),
        "Membership": obj(membership, membership),
        "Participation": obj(participation, participation),
        "ProfileInput": obj({**basic, **metadata}, ("name", "course_id", "semester")),
        "ProfileUpdate": obj({**basic, **metadata}),
        "ProfileOptions": obj(
            {
                "courses": array(course_option),
                "fields": array(option),
                "semesters": array({"type": "integer"}),
                "statuses": array(string()),
                "types": array(string()),
            },
            ("courses", "fields", "semesters", "statuses", "types"),
        ),
        "Entities": array(option),
        "ProjectInput": obj(project, project),
        "ProjectUpdate": obj(project),
        "Project": obj(
            {"id": string(), "creator_id": string(nullable=True), **project},
            ("id", "creator_id", *project),
        ),
        "Projects": array(ref("Project")),
        "ReviewInput": obj(
            {"status": {"type": "string", "enum": ["confirmed", "rejected"]}},
            ("status",),
        ),
        "Participations": array(
            obj(
                {
                    "profile_id": string(),
                    "profile_name": string(),
                    "participation": ref("Participation"),
                },
                ("profile_id", "profile_name", "participation"),
            )
        ),
        "CurrentPasswordInput": obj(
            {"current_password": string()}, ("current_password",)
        ),
        "EmailInput": obj(
            {"current_password": string(), "new_email": string()},
            ("current_password", "new_email"),
        ),
        "PasswordInput": obj(
            {
                "current_password": string(),
                "new_password": {**string(), "minLength": 8},
            },
            ("current_password", "new_password"),
        ),
        "PhotoInput": obj(
            {"photo": {"type": "string", "format": "binary"}}, ("photo",)
        ),
        "ConnectionInput": obj({"target_user_id": string()}, ("target_user_id",)),
        "Connection": obj(
            {
                "id": string(),
                "user_a_id": string(),
                "user_b_id": string(),
                "requested_by": string(),
                "status": {"type": "string", "enum": ["pending", "accepted"]},
                "created_at": {"type": "string", "format": "date-time"},
                "accepted_at": {
                    "type": "string",
                    "format": "date-time",
                    "nullable": True,
                },
            },
            (
                "id",
                "user_a_id",
                "user_b_id",
                "requested_by",
                "status",
                "created_at",
                "accepted_at",
            ),
        ),
        "Connections": obj({"connections": array(ref("Connection"))}, ("connections",)),
        "Edge": obj(
            {
                "id": string(),
                "source": string(),
                "target": string(),
                "type": {"type": "string", "enum": ["close", "class", "entity", "ic"]},
                "context": {"type": "object", "additionalProperties": True},
            },
            ("id", "source", "target", "type", "context"),
        ),
        "Graph": obj(
            {"nodes": array(ref("Profile")), "edges": array(ref("Edge"))},
            ("nodes", "edges"),
        ),
        "PathResult": obj({"path": path, "graph": ref("Graph")}, ("path", "graph")),
        "NetworkStats": obj({"people": {"type": "integer"}}, ("people",)),
        "SearchInput": obj(
            {
                "query": {**string(4000), "minLength": 1},
                "mode": {
                    "type": "string",
                    "enum": ["proximity", "relevance"],
                    "default": "proximity",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                },
                "offset": {"type": "integer", "minimum": 0, "default": 0},
            },
            ("query",),
        ),
        "SearchResult": obj(
            {
                "results": array(
                    obj(
                        {
                            "profile_id": string(),
                            "similarity": {
                                "type": "number",
                                "minimum": -1,
                                "maximum": 1,
                            },
                            "cost": {**cost, "nullable": True},
                            "path": path,
                        },
                        ("profile_id", "similarity", "cost", "path"),
                    )
                ),
                "total": {"type": "integer"},
                "mode": string(),
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
                "indexing_pending": {"type": "integer"},
                "graph": ref("Graph"),
            },
            (
                "results",
                "total",
                "mode",
                "limit",
                "offset",
                "indexing_pending",
                "graph",
            ),
        ),
    }
    full = {
        **basic,
        **metadata,
        "id": string(),
        "course": string(),
        "field": string(),
        "photo_id": string(nullable=True),
        "photo_url": string(nullable=True),
        "entities": array(option),
        "research_projects": array(ref("Project")),
    }
    full.update(
        experiences=array(ref("Experience")),
        entity_memberships=array(ref("Membership")),
        research_participations=array(ref("Participation")),
    )
    model["Profile"] = obj(full, full)
    model["LoginInput"]["example"] = {
        "email": "ana.seed@al.insper.edu.br",
        "password": "GrafoNetDev!2026",
    }
    model["SearchInput"]["example"] = {
        "query": "alguém com experiência em dados e fintechs",
        "mode": "proximity",
        "limit": 10,
        "offset": 0,
    }
    model["ProfileInput"]["example"] = {
        "name": "Pessoa",
        "course_id": "computer-science",
        "semester": 2,
        "field_id": "technology",
        "bio": "Estudo computação",
        "type": "aluno",
    }
    for name in ("ExperienceInput", "MembershipInput", "ParticipationInput"):
        model[name]["properties"]["id"]["description"] = (
            "Omitir em novos registros; na edição, usar somente o id existente do próprio perfil."
        )
    return deepcopy(model)
