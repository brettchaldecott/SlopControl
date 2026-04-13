"""Example: Simple Bracket Design"""

from llmcad import Box, Circle, Rect, extrude, fillet, snapshot


def create_simple_bracket():
    """Create a simple L-shaped bracket."""
    base = Box(80, 60, 5)

    wall = Rect(5, 60).place_on(base.right)
    wall_body = extrude(wall, amount=40)
    result = base + wall_body

    result = fillet(result.top.edges, radius=2)

    snapshot(result, "simple_bracket")
    return result


if __name__ == "__main__":
    bracket = create_simple_bracket()
    print("Created simple bracket")
