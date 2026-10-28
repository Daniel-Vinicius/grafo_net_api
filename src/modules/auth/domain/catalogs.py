COURSES = [
    {"id": "computer-science", "name": "Ciência da Computação"},
    {"id": "economics", "name": "Economia"},
    {"id": "law", "name": "Direito"},
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
