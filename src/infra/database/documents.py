from dataclasses import asdict


def document(value):
    result = asdict(value)
    result["_id"] = result.pop("id")
    return result


def attributes(value):
    result = dict(value)
    result["id"] = str(result.pop("_id"))
    return result
