from __future__ import annotations

from typing import Dict, Optional

try:
    from libxmp import XMPFiles, consts  # type: ignore
    _HAS_XMP = True
except Exception:
    _HAS_XMP = False


def extract_xmp_from_bytes(image_path: Optional[str] = None) -> Dict[str, str]:
    if not _HAS_XMP or image_path is None:
        return {}
    try:
        xmpfile = XMPFiles(file_path=image_path, open_forupdate=False)
        xmp = xmpfile.get_xmp()
        xmpfile.close_file()
        if xmp is None:
            return {}
        props: Dict[str, str] = {}
        for schema in xmp.iter_schemas():
            for prop, value, _ in xmp.properties(schema):
                try:
                    props[f"{schema}:{prop}"] = str(value)
                except Exception:
                    pass
        return props
    except Exception:
        return {}


