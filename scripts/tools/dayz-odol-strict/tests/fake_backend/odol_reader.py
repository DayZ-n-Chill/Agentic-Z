"""Original test double for the isolated worker; it parses no ODOL bytes."""

import json
from types import SimpleNamespace


class ODOL:
    @classmethod
    def from_bytes(cls, data):
        if data == b"FAIL":
            raise ValueError("directed fake backend failure")
        value = json.loads(data.decode("utf-8"))
        lods = []
        for item in value["lods"]:
            if item is None:
                lods.append(None)
                continue
            selections = [
                SimpleNamespace(name=name)
                for name in item.get("selection_names", [])
            ]
            materials = [
                SimpleNamespace(material_name=name)
                for name in item.get("material_names", [])
            ]
            lods.append(SimpleNamespace(
                faces=[None] * item.get("face_count", 0),
                materials=materials,
                named_properties=item.get("named_properties", []),
                named_selections=selections,
                normals=[None] * item.get("normal_count", 0),
                proxies=[None] * item.get("proxy_count", 0),
                resolution=item["resolution"],
                vertices=[None] * item.get("vertex_count", 0),
            ))
        return SimpleNamespace(
            lod_actual_end=value["lod_actual_end"],
            lod_end_table=value["lod_end_table"],
            lod_errors=value.get("lod_errors", {}),
            lod_start_table=value["lod_start_table"],
            lods=lods,
            n_lods=value["n_lods"],
            resolutions=value["resolutions"],
            version=value["version"],
        )
