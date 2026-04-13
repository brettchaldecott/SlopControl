"""Example: Gear Mechanism Design"""

from llmcad import Cylinder, Box, Circle, Polygon, extrude, cut, export_stl


def create_simple_gear():
    """Create a simplified gear-like cylindrical part with holes."""
    outer = Cylinder(radius=30, height=10)

    hub = Cylinder(radius=10, height=12)
    outer = outer + hub

    teeth_count = 12
    for i in range(teeth_count):
        angle = (360.0 / teeth_count) * i
        tooth = Box(8, 8, 5)
        tooth = tooth.rotate(z=angle)
        tooth = tooth.translate(x=30)
        outer = outer + tooth

    center_hole = Cylinder(radius=5, height=15)
    gear = outer - center_hole

    for bolt_r, bolt_y in [(6, 15), (6, -15)]:
        bolt_hole = Cylinder(radius=bolt_r, height=15)
        bolt_hole = bolt_hole.translate(y=bolt_y)
        gear = gear - bolt_hole

    export_stl(gear, "gear.stl")
    return gear


if __name__ == "__main__":
    gear = create_simple_gear()
    print("Created gear mechanism")
