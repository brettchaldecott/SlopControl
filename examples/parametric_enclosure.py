"""Example: Parametric Enclosure Design"""

from llmcad import Box, shell, fillet, export_step


def create_parametric_enclosure(
    width: float = 80,
    height: float = 50,
    depth: float = 30,
    wall_thickness: float = 2,
):
    """Create a parametric hollow enclosure box."""
    outer = Box(width, height, depth)

    inner_dimensions = (
        width - 2 * wall_thickness,
        height - 2 * wall_thickness,
        depth - wall_thickness,
    )

    enclosure = shell(outer.top, thickness=wall_thickness)

    enclosure = fillet(enclosure.bottom.edges, radius=1)

    export_step(enclosure, f"enclosure_{width}x{height}x{depth}.step")
    return enclosure


if __name__ == "__main__":
    enclosure = create_parametric_enclosure()
    print("Created parametric enclosure")
