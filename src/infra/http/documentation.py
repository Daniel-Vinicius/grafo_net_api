def documented(
    tag, summary, response=None, body=None, status=200, public=False, multipart=False
):
    def decorate(function):
        operation = {
            "tags": [tag],
            "summary": summary,
            "operationId": function.__name__,
            "security": [] if public else [{"bearerAuth": []}],
            "responses": {str(status): {"description": "Operação concluída"}},
        }
        if response:
            operation["responses"][str(status)]["content"] = {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{response}"}
                }
            }
        if body:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "multipart/form-data" if multipart else "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{body}"}
                    }
                },
            }
        for code in (400, 401, 403, 404, 409, 413, 503):
            operation["responses"][str(code)] = {
                "description": {
                    400: "Entrada inválida",
                    401: "Autenticação inválida",
                    403: "Acesso negado",
                    404: "Recurso ausente",
                    409: "Conflito",
                    413: "Arquivo acima do limite",
                    503: "Serviço indisponível",
                }[code],
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                },
            }
        function.openapi = operation
        return function

    return decorate
