"""Template: Cable Gland / Strain Relief

This template creates a cylindrical cable gland for passing cables through panels.
"""

from llmcad import Cylinder, Box, chamfer, export_step


def create_cable_gland(
    body_diameter: float = 20,
    body_height: float = 10,
    thread_diameter: float = 16,
    thread_height: float = 8,
    cable_diameter: float = 6,
    nut_height: float = 4,
):
    """Create a cable gland for panel mounting.

    Args:
        body_diameter: Diameter of the body in mm
        body_height: Height of the main body in mm
        thread_diameter: Outer diameter of thread in mm
        thread_height: Height of threaded section in mm
        cable_diameter: Diameter of cable hole in mm
        nut_height: Height of locking nut in mm
    """
    body = Cylinder(body_diameter / 2, body_height)

    thread = Cylinder(thread_diameter / 2, thread_height)
    thread = thread.translate(z=body_height)

    gland = body + thread

    cable_hole = Cylinder(cable_diameter / 2 + 1, body_height + thread_height + 2)
    gland = gland - cable_hole

    gland = chamfer(gland.top.edges, distance=0.5)

    nut = Cylinder(body_diameter / 2 + 1, nut_height)
    nut_outer = Cylinder(body_diameter / 2 + 3, nut_height)
    nut = nut_outer - nut
    nut = nut.translate(z=body_height + thread_height - nut_height)

    export_step(gland, f"gland_{body_diameter}x{body_height}.step")
    export_step(nut, f"gland_nut_{body_diameter}.step")

    return gland, nut


if __name__ == "__main__":
    gland, nut = create_cable_gland()
    print("Created cable gland and nut")
