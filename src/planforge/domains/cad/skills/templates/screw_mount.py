"""Template: Screw Mount with Counterbore

This template creates a screw mount with a counterbore hole
for flush fastening.
"""

from llmcad import Cylinder, Box, Circle, extrude, union, chamfer


def create_screw_mount(
    head_radius: float = 6,
    head_height: float = 3,
    shaft_radius: float = 3,
    shaft_height: float = 10,
    base_width: float = 20,
    base_height: float = 20,
    base_thickness: float = 3,
):
    """Create a screw mount with counterbore hole.

    Args:
        head_radius: Radius of screw head in mm
        head_height: Height of screw head in mm
        shaft_radius: Radius of screw shaft hole in mm
        shaft_height: Depth of screw hole in mm
        base_width: Width of mounting base in mm
        base_height: Height of mounting base in mm
        base_thickness: Thickness of base in mm
    """
    base = Box(base_width, base_height, base_thickness)

    boss = Cylinder(head_radius * 1.2, head_height + shaft_height)
    boss = boss.translate(z=base_thickness)
    mount = union(base, boss)

    head_hole = Cylinder(head_radius, head_height + 1)
    head_hole = head_hole.translate(z=base_thickness)
    mount = mount - head_hole

    shaft_hole = Cylinder(shaft_radius, shaft_height)
    shaft_hole = shaft_hole.translate(z=base_thickness - shaft_height + 1)
    mount = mount - shaft_hole

    mount = chamfer(mount.top.edges, distance=0.5)

    return mount


if __name__ == "__main__":
    mount = create_screw_mount()
    print("Created screw mount")
