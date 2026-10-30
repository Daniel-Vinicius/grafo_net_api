COURSES = [
    {"id": "administration", "name": "Administração", "semesters": 8},
    {"id": "computer-science", "name": "Ciência da Computação", "semesters": 8},
    {"id": "law", "name": "Direito", "semesters": 8},
    {"id": "economics", "name": "Economia", "semesters": 8},
    {"id": "computer-engineering", "name": "Engenharia de Computação", "semesters": 10},
    {"id": "production-engineering", "name": "Engenharia de Produção", "semesters": 10},
    {"id": "mechanical-engineering", "name": "Engenharia Mecânica", "semesters": 10},
    {
        "id": "mechatronic-engineering",
        "name": "Engenharia Mecatrônica",
        "semesters": 10,
    },
]
FIELDS = [
    {"id": "finance", "name": "Mercado financeiro"},
    {"id": "technology", "name": "Tecnologia"},
    {"id": "entrepreneurship", "name": "Empreendedorismo"},
    {"id": "cybersecurity", "name": "Cybersegurança"},
]
STATUSES = ["planned", "in_progress", "completed", "cancelled"]
ENTITIES = [
    {"id": slug, "name": name}
    for slug, name in [
        ("insper-code", "Insper Code"),
        ("insper-jr", "Insper Jr"),
        ("insper-sec", "Insper Sec"),
        ("insper-ai", "Insper AI"),
        ("fintech", "Fintech"),
        ("infinance", "Infinance"),
        ("investe-insper", "Investe Insper"),
        ("baja", "Baja"),
        ("madfox", "Madfox"),
        ("cursinho-insper", "Cursinho Insper"),
        ("diretorio-academico", "Diretório Acadêmico"),
    ]
]
