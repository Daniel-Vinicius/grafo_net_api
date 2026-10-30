from modules.auth.domain.catalogs import COURSES, FIELDS, STATUSES


class GetProfileOptionsUseCase:
    def __init__(self):
        pass

    def execute(self):
        return {
            "courses": COURSES,
            "fields": FIELDS,
            "semesters": list(range(1, 11)),
            "statuses": STATUSES,
            "types": ["aluno", "alumni", "professor"],
        }
