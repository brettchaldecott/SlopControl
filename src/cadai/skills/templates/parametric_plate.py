"""Template: Parametric Plate with Mounting Holes

This template demonstrates the common pattern of creating
a plate with corner mounting holes.
"""

from llmcad import Box, Circle, extrude, fillet, snapshot


def create_mounting_plate(
    width: float = 100,
    height: float = 60,
    thickness: float = 5,
    hole_radius: float = 5,
    inset: float = 8,
    fillet_radius: float = 2,
):
    """Create a mounting plate with corner holes and filleted edges.

    Args:
        width: Plate width in mm
        height: Plate height in mm
        thickness: Plate thickness in mm
        hole_radius: Radius of mounting holes in mm
        inset: Distance from corner to hole center in mm
        fillet_radius: Fillet radius for top edges in mm
    """
    plate = Box(width, height, thickness)

    corner_positions = [
        (inset, inset),
        (width - inset, inset),
        (inset, height - inset),
        (width - inset, height - inset),
    ]

    for x, y in corner_positions:
        hole = Circle(hole_radius).place_on(plate.top, at=(x, y))
        cut_hole = extrude(hole, through=True)
        plate = plate - cut_hole

    if fillet_radius > 0:
        plate = fillet(plate.top.edges, radius=fillet_radius)

    snapshot(plate, f"mounting_plate_{width}x{height}")
    return plate


if __name__ == "__main__":
    plate = create_mounting_plate()
    print("Created mounting plate")
