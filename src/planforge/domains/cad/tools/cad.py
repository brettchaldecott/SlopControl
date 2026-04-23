from typing import Any, Literal, Optional

from langchain_core.tools import tool

from llmcad import (
    Box,
    Cylinder,
    Sphere,
    Rect,
    Circle,
    Ellipse,
    Polygon,
    Text,
    Sketch,
    Body,
    extrude,
    revolve,
    loft,
    sweep,
    fillet,
    chamfer,
    shell,
    split,
    mirror,
    export_step,
    export_stl,
    export_glb,
)

from ..utils.cad_helpers import serialize_body, get_model_info


def _body_to_dict(body: Body) -> dict:
    return serialize_body(body)


def _parse_edges(edges_str: str) -> str:
    return edges_str


@tool
def create_box(
    width: float,
    height: float,
    depth: float,
    name: Optional[str] = None,
) -> str:
    """Create a 3D box/cuboid shape.

    Args:
        width: Width along X-axis in mm
        height: Height along Y-axis in mm
        depth: Depth along Z-axis in mm
        name: Optional name for the body (e.g., 'base_plate', 'bracket')

    Returns:
        JSON-serialized body object
    """
    body = Box(width, height, depth)
    return _body_to_dict({"body": body, "name": name or "box"})


@tool
def create_cylinder(
    radius: float,
    height: float,
    axis: str = "z",
    name: Optional[str] = None,
) -> str:
    """Create a 3D cylinder shape.

    Args:
        radius: Radius in mm
        height: Height along axis in mm
        axis: Axis direction ('x', 'y', or 'z', default 'z')
        name: Optional name for the body

    Returns:
        JSON-serialized body object
    """
    body = Cylinder(radius, height)
    return _body_to_dict({"body": body, "name": name or "cylinder"})


@tool
def create_sphere(
    radius: float,
    name: Optional[str] = None,
) -> str:
    """Create a 3D sphere shape.

    Args:
        radius: Radius in mm
        name: Optional name for the body

    Returns:
        JSON-serialized body object
    """
    body = Sphere(radius)
    return _body_to_dict({"body": body, "name": name or "sphere"})


@tool
def create_rect(
    width: float,
    height: float,
    name: Optional[str] = None,
) -> str:
    """Create a rectangular sketch on the XY plane.

    Args:
        width: Width in mm
        height: Height in mm
        name: Optional name for the sketch

    Returns:
        JSON-serialized sketch object
    """
    sketch = Rect(width, height)
    return _body_to_dict({"sketch": sketch, "name": name or "rect"})


@tool
def create_circle(
    radius: float,
    name: Optional[str] = None,
) -> str:
    """Create a circular sketch on the XY plane.

    Args:
        radius: Radius in mm
        name: Optional name for the sketch

    Returns:
        JSON-serialized sketch object
    """
    sketch = Circle(radius)
    return _body_to_dict({"sketch": sketch, "name": name or "circle"})


@tool
def create_ellipse(
    x_radius: float,
    y_radius: float,
    name: Optional[str] = None,
) -> str:
    """Create an elliptical sketch on the XY plane.

    Args:
        x_radius: Radius along X-axis in mm
        y_radius: Radius along Y-axis in mm
        name: Optional name for the sketch

    Returns:
        JSON-serialized sketch object
    """
    sketch = Ellipse(x_radius, y_radius)
    return _body_to_dict({"sketch": sketch, "name": name or "ellipse"})


@tool
def create_polygon(
    sides: int,
    radius: float,
    name: Optional[str] = None,
) -> str:
    """Create a regular polygon sketch on the XY plane.

    Args:
        sides: Number of sides (3 = triangle, 4 = square, 5 = pentagon, etc.)
        radius: Circumradius (distance from center to vertex) in mm
        name: Optional name for the sketch

    Returns:
        JSON-serialized sketch object
    """
    sketch = Polygon(sides, radius)
    return _body_to_dict({"sketch": sketch, "name": name or "polygon"})


@tool
def extrude_sketch(
    sketch_data: str,
    amount: float,
    through: bool = False,
    direction: Optional[str] = None,
) -> str:
    """Extrude a sketch to create a 3D body.

    Args:
        sketch_data: JSON data containing the sketch from create_* tools
        amount: Extrusion distance in mm (ignored if through=True)
        through: If True, extrude through all
        direction: Direction for extrusion ('up', 'down', 'both', or None for default)

    Returns:
        JSON-serialized body object
    """
    import json

    data = json.loads(sketch_data)
    sketch = data["sketch"]

    body = extrude(sketch, amount=amount if not through else None, through=through)
    return _body_to_dict({"body": body, "name": data.get("name", "extruded")})


@tool
def revolve_sketch(
    sketch_data: str,
    angle: float = 360,
    axis: Optional[str] = None,
) -> str:
    """Revolve a sketch around an axis to create a 3D body.

    Args:
        sketch_data: JSON data containing the sketch
        angle: Revolution angle in degrees (default 360)
        axis: Axis to revolve around (optional, uses default if not specified)

    Returns:
        JSON-serialized body object
    """
    import json

    data = json.loads(sketch_data)
    sketch = data["sketch"]

    body = revolve(sketch, angle=angle)
    return _body_to_dict({"body": body, "name": data.get("name", "revolved")})


@tool
def add_fillet(
    body_data: str,
    radius: float,
    edges: Optional[str] = None,
) -> str:
    """Add fillet (rounded edge) to a body.

    Args:
        body_data: JSON data containing the body
        radius: Fillet radius in mm
        edges: Which edges to fillet (e.g., 'top.edges', 'top.front.edges', or 'all')

    Returns:
        JSON-serialized body object
    """
    import json

    data = json.loads(body_data)
    body = data["body"]

    if edges == "all" or edges is None:
        all_edges = (
            body.top.edges
            + body.bottom.edges
            + body.front.edges
            + body.back.edges
            + body.left.edges
            + body.right.edges
        )
        result = fillet(all_edges, radius=radius)
    elif edges:
        parts = edges.split(".")
        face = getattr(body, parts[0], None)
        if face:
            if len(parts) > 1:
                face = getattr(face, parts[1], None)
            if face and hasattr(face, "edges"):
                result = fillet(face.edges, radius=radius)
            else:
                result = body
        else:
            result = body
    else:
        result = fillet(body.top.edges, radius=radius)

    return _body_to_dict({"body": result, "name": data.get("name", "fillet")})


@tool
def add_chamfer(
    body_data: str,
    distance: float,
    edges: Optional[str] = None,
) -> str:
    """Add chamfer (beveled edge) to a body.

    Args:
        body_data: JSON data containing the body
        distance: Chamfer distance in mm
        edges: Which edges to chamfer (optional)

    Returns:
        JSON-serialized body object
    """
    import json

    data = json.loads(body_data)
    body = data["body"]

    if edges == "all" or edges is None:
        all_edges = (
            body.top.edges
            + body.bottom.edges
            + body.front.edges
            + body.back.edges
            + body.left.edges
            + body.right.edges
        )
        result = chamfer(all_edges, distance=distance)
    elif edges:
        parts = edges.split(".")
        face = getattr(body, parts[0], None)
        if face:
            if len(parts) > 1:
                face = getattr(face, parts[1], None)
            if face and hasattr(face, "edges"):
                result = chamfer(face.edges, distance=distance)
            else:
                result = body
        else:
            result = body
    else:
        result = chamfer(body.top.edges, distance=distance)

    return _body_to_dict({"body": result, "name": data.get("name", "chamfer")})


@tool
def create_shell(
    body_data: str,
    thickness: float,
    face: str = "top",
) -> str:
    """Create a shell (hollow) from a body by removing a face.

    Args:
        body_data: JSON data containing the body
        thickness: Wall thickness in mm
        face: Which face to open ('top', 'bottom', 'front', 'back', 'left', 'right')

    Returns:
        JSON-serialized body object
    """
    import json

    data = json.loads(body_data)
    body = data["body"]
    face_obj = getattr(body, face, None)

    if face_obj:
        result = shell(face_obj, thickness=thickness)
    else:
        result = body

    return _body_to_dict({"body": result, "name": data.get("name", "shelled")})


@tool
def mirror_body(
    body_data: str,
    plane: str = "xz",
) -> str:
    """Mirror a body across a plane.

    Args:
        body_data: JSON data containing the body
        plane: Mirror plane ('xy', 'xz', or 'yz')

    Returns:
        JSON-serialized body object
    """
    import json

    data = json.loads(body_data)
    body = data["body"]

    result = mirror(body, plane=plane)
    return _body_to_dict({"body": result, "name": data.get("name", "mirrored")})


@tool
def union_bodies(
    body1_data: str,
    body2_data: str,
) -> str:
    """Unite (merge) two bodies together using the + operator.

    Args:
        body1_data: JSON data containing the first body
        body2_data: JSON data containing the second body

    Returns:
        JSON-serialized body object
    """
    from ..utils.cad_helpers import deserialize_body

    data1 = deserialize_body(body1_data)
    data2 = deserialize_body(body2_data)

    result = data1["body"] + data2["body"]
    return _body_to_dict(
        {"body": result, "name": f"{data1.get('name', 'b1')}_union_{data2.get('name', 'b2')}"}
    )


@tool
def cut_body(
    body1_data: str,
    body2_data: str,
) -> str:
    """Cut body2 from body1 using the - operator (boolean subtraction).

    Args:
        body1_data: JSON data containing the base body
        body2_data: JSON data containing the body to cut

    Returns:
        JSON-serialized body object
    """
    from ..utils.cad_helpers import deserialize_body

    data1 = deserialize_body(body1_data)
    data2 = deserialize_body(body2_data)

    result = data1["body"] - data2["body"]
    return _body_to_dict(
        {"body": result, "name": f"{data1.get('name', 'b1')}_cut_{data2.get('name', 'b2')}"}
    )


@tool
def intersect_bodies(
    body1_data: str,
    body2_data: str,
) -> str:
    """Intersect two bodies using the & operator (keep only overlapping volume).

    Args:
        body1_data: JSON data containing the first body
        body2_data: JSON data containing the second body

    Returns:
        JSON-serialized body object
    """
    from ..utils.cad_helpers import deserialize_body

    data1 = deserialize_body(body1_data)
    data2 = deserialize_body(body2_data)

    result = data1["body"] & data2["body"]
    return _body_to_dict(
        {"body": result, "name": f"{data1.get('name', 'b1')}_intersect_{data2.get('name', 'b2')}"}
    )


@tool
def export_model(
    body_data: str,
    format: str,
    path: str,
) -> str:
    """Export a body to a CAD file format.

    Args:
        body_data: JSON data containing the body
        format: Export format ('step', 'stl', or 'glb')
        path: Output file path (e.g., 'output.step', 'output.stl')

    Returns:
        Confirmation message with file path
    """
    import json

    data = json.loads(body_data)
    body = data["body"]

    format_lower = format.lower()
    if format_lower == "step":
        export_step(body, path)
    elif format_lower == "stl":
        export_stl(body, path)
    elif format_lower == "glb":
        export_glb(body, path)
    else:
        return f"Error: Unsupported format '{format}'. Use 'step', 'stl', or 'glb'."

    return f"Exported to {path}"


@tool
def get_body_info(body_data: str) -> str:
    """Get information about a body (dimensions, volume, etc.).

    Args:
        body_data: JSON data containing the body

    Returns:
        JSON string with body information
    """
    import json

    data = json.loads(body_data)
    body = data["body"]

    info = get_model_info(body)
    info["name"] = data.get("name", "unnamed")
    return json.dumps(info, indent=2)


CAD_TOOLS = [
    create_box,
    create_cylinder,
    create_sphere,
    create_rect,
    create_circle,
    create_ellipse,
    create_polygon,
    extrude_sketch,
    revolve_sketch,
    add_fillet,
    add_chamfer,
    create_shell,
    mirror_body,
    union_bodies,
    cut_body,
    intersect_bodies,
    export_model,
    get_body_info,
]
