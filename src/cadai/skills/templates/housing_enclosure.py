"""Template: Housing/Enclosure with Lid

This template creates a box with a hollow interior and a separate lid.
"""

from llmcad import Box, shell, chamfer, export_step


def create_housing(
    width: float = 80,
    height: float = 50,
    depth: float = 30,
    wall_thickness: float = 2,
    lid_gap: float = 0.5,
):
    """Create a housing/enclosure with a hollow interior.

    Args:
        width: Outer width in mm
        height: Outer height in mm
        depth: Outer depth in mm
        wall_thickness: Wall thickness in mm
        lid_gap: Gap between lid and housing in mm
    """
    outer = Box(width, height, depth)

    inner_height = height - wall_thickness - lid_gap
    housing = shell(outer.top, thickness=wall_thickness)

    housing = chamfer(housing.bottom.edges, distance=0.5)

    lid = Box(width - lid_gap * 2, lid_gap, depth - lid_gap * 2)
    lid = chamfer(lid.bottom.edges, distance=0.3)

    export_step(housing, f"housing_{width}x{height}x{depth}.step")
    export_step(lid, f"lid_{width}x{height}x{depth}.step")

    return housing, lid


if __name__ == "__main__":
    housing, lid = create_housing()
    print("Created housing and lid")
