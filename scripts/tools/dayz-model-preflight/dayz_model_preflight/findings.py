SEVERITY_ORDER = {"ERROR": 0, "WARN": 1}


def finding(
    code,
    severity,
    message,
    lod_index=None,
    face_index=None,
    selection=None,
    **details
):
    value = {
        "code": code,
        "severity": severity,
        "message": message,
        "lod_index": lod_index,
    }
    if face_index is not None:
        value["face_index"] = face_index
    if selection is not None:
        value["selection"] = selection
    value.update(details)
    return value


def sort_findings(findings):
    return sorted(
        findings,
        key=lambda item: (
            SEVERITY_ORDER.get(item["severity"], 99),
            item["code"],
            -1 if item.get("lod_index") is None else item["lod_index"],
            -1 if item.get("face_index") is None else item["face_index"],
            item.get("selection") or "",
        ),
    )
