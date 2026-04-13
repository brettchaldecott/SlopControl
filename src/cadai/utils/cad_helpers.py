import json
from typing import Any, Optional

from llmcad import Body


def serialize_body(data: dict) -> str:
    """Serialize a body or sketch to JSON for tool return.

    llmcad bodies are complex objects that can't be directly serialized.
    We store them in a registry and return a reference.

    Args:
        data: Dict with 'body' or 'sketch' key and optional 'name'

    Returns:
        JSON string with reference ID
    """
    body_registry = _get_registry()
    ref_id = f"body_{len(body_registry)}"
    body_registry[ref_id] = data
    return json.dumps({"ref": ref_id, "name": data.get("name", "unnamed")})


def deserialize_body(data: str) -> dict:
    """Deserialize a body reference back to actual object.

    Args:
        data: JSON string from serialize_body

    Returns:
        Dict with body/sketch and name
    """
    import json

    parsed = json.loads(data)
    ref_id = parsed.get("ref")

    if not ref_id:
        return parsed

    body_registry = _get_registry()
    if ref_id in body_registry:
        return body_registry[ref_id]
    return parsed


def get_registry() -> dict:
    """Get the body registry for current context."""
    return _get_registry()


def clear_registry() -> None:
    """Clear the body registry."""
    global _body_registry
    _body_registry = {}


_body_registry: dict = {}


def _get_registry() -> dict:
    global _body_registry
    if _body_registry is None:
        _body_registry = {}
    return _body_registry


def get_model_info(body: Body) -> dict:
    """Extract information from a body.

    Args:
        body: llmcad Body object

    Returns:
        Dict with dimensions and properties
    """
    info = {
        "type": "unknown",
        "dimensions": {},
    }

    try:
        if hasattr(body, "BoundingBox"):
            bbox = body.BoundingBox
            info["dimensions"] = {
                "width": bbox.xlen,
                "height": bbox.ylen,
                "depth": bbox.zlen,
            }
            info["bounding_box"] = {
                "x_min": bbox.xmin,
                "x_max": bbox.xmax,
                "y_min": bbox.ymin,
                "y_max": bbox.ymax,
                "z_min": bbox.zmin,
                "z_max": bbox.zmax,
            }
    except Exception:
        pass

    try:
        if hasattr(body, "Volume"):
            info["volume"] = body.Volume
    except Exception:
        pass

    try:
        if hasattr(body, "Area"):
            info["surface_area"] = body.Area
    except Exception:
        pass

    try:
        if hasattr(body, "Faces"):
            info["face_count"] = len(body.Faces)
    except Exception:
        pass

    try:
        if hasattr(body, "Edges"):
            info["edge_count"] = len(body.Edges)
    except Exception:
        pass

    return info


def validate_dimensions(**dims: float) -> tuple[bool, Optional[str]]:
    """Validate that dimensions are positive numbers.

    Args:
        **dims: Named dimensions to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    for name, value in dims.items():
        if not isinstance(value, (int, float)):
            return False, f"{name} must be a number, got {type(value).__name__}"
        if value <= 0:
            return False, f"{name} must be positive, got {value}"
    return True, None
