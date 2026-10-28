"""Repository architecture lint; intentionally outside the pytest suite."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = (
    "pymongo",
    "gridfs",
    "bson",
    "smtplib",
    "bcrypt",
    "PIL",
    "dotenv",
    "click",
    "urllib.request",
    "urllib.error",
    "flask_jwt_extended",
    "apispec",
    "apispec_webframeworks",
    "flask_swagger_ui",
)


def check():
    problems = []

    def reject(path, text):
        problems.append(f"{path.relative_to(ROOT)}: {text}")

    for path in sorted((ROOT / "src").rglob("*.py")):
        relative = path.relative_to(ROOT / "src")
        parts = relative.parts
        test = path.name.startswith("test_")
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
        if test and not ({"domain", "routes"} & set(parts)):
            reject(
                path,
                "testes somente em domain ou routes; UseCases são verificados pelas rotas",
            )
        if test and "repositories" in parts:
            reject(path, "não manter testes de repositório ou mapeamento")
        if "repositories" in parts and not test and path.name != "__init__.py":
            tail = parts[parts.index("repositories") + 1 :]
            valid = (len(tail) == 2 and tail[1] == "contract.py") or (
                len(tail) == 3
                and (
                    tail[1] == "mongo"
                    and tail[2] in ("repository.py", "schema.py")
                    or tail[1] == "in_memory"
                    and tail[2] == "repository.py"
                )
            )
            if not valid:
                reject(path, "separar repositórios por recurso, contrato e adaptador")
        if "useCases" in parts:
            if path.name in ("__init__.py", "conftest.py"):
                continue
            folder = path.parent.name
            expected = ("test_" if test else "") + folder + "UseCase.py"
            if path.name != expected:
                reject(path, f"usar {expected}")
            if not test:
                classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
                name = folder[0].upper() + folder[1:] + "UseCase"
                if len(classes) != 1 or classes[0].name != name:
                    reject(path, f"definir somente a classe {name}")
                elif [
                    node.name
                    for node in classes[0].body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not node.name.startswith("_")
                ] != ["execute"]:
                    reject(path, "caso de uso tem somente a ação pública execute")
        if any(
            isinstance(node, ast.ClassDef)
            and node.name in ("Store", "MongoStore", "MemoryStore")
            for node in tree.body
        ):
            reject(path, "usar repositórios diretos, sem camada Store genérica")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            names = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [item.name for item in node.names]
            )
            for name in names:
                if test:
                    if ".mongo." in name or name.startswith(
                        (
                            "pymongo",
                            "gridfs",
                            "bson",
                            "smtplib",
                            "urllib.request",
                            "unittest.mock",
                            "infra.database.seed",
                        )
                    ):
                        reject(
                            path,
                            "teste não pode acessar adaptadores externos ou banco real",
                        )
                    continue
                if "domain" in parts and (
                    name.startswith(("infra", "flask"))
                    or ".repositories" in name
                    or ".useCases" in name
                    or ".routes" in name
                ):
                    reject(path, f"domínio não depende de {name}")
                if "repositories" in parts and (
                    ".useCases" in name or ".routes" in name
                ):
                    reject(path, f"repositório não depende de {name}")
                if "useCases" in parts or "routes" in parts:
                    if ".repositories." in name and not name.endswith(".contract"):
                        reject(path, f"injetar repositório por contrato: {name}")
                    if name.startswith("infra.") and not (
                        name.endswith((".contract", ".context", ".errors"))
                        or "routes" in parts
                        and name.startswith("infra.http.")
                    ):
                        reject(path, f"injetar serviço por contrato: {name}")
                external = any(
                    name == prefix or name.startswith(prefix + ".")
                    for prefix in EXTERNAL
                )
                if (
                    external
                    and parts[0] != "infra"
                    and not ("repositories" in parts and "mongo" in parts)
                ):
                    reject(
                        path,
                        f"integração externa fora de infra/adaptador Mongo: {name}",
                    )
                if (
                    name.startswith("flask")
                    and parts[0] != "infra"
                    and "routes" not in parts
                    and path.name != "app.py"
                ):
                    reject(
                        path,
                        "Flask somente na infraestrutura HTTP, rotas e entrada da aplicação",
                    )
    for path in (ROOT / "tests").rglob("test_*.py"):
        reject(path, "tests contém somente suporte; suítes ficam junto do código")
    return problems


if __name__ == "__main__":
    errors = check()
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("Estrutura e dependências corretas")
