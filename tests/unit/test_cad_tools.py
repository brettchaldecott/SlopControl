"""Tests for CAD tools."""

import pytest


class TestCadTools:
    """Test suite for CAD tool functions."""

    def test_create_box_tool(self):
        """Test box creation tool exists and is callable."""
        from slopcontrol.domains.cad.tools.cad import create_box

        assert create_box is not None
        assert hasattr(create_box, "invoke")

    def test_create_cylinder_tool(self):
        """Test cylinder creation tool exists and is callable."""
        from slopcontrol.domains.cad.tools.cad import create_cylinder

        assert create_cylinder is not None
        assert hasattr(create_cylinder, "invoke")

    def test_create_sphere_tool(self):
        """Test sphere creation tool exists and is callable."""
        from slopcontrol.domains.cad.tools.cad import create_sphere

        assert create_sphere is not None
        assert hasattr(create_sphere, "invoke")

    def test_create_circle_tool(self):
        """Test circle sketch creation tool exists."""
        from slopcontrol.domains.cad.tools.cad import create_circle

        assert create_circle is not None
        assert hasattr(create_circle, "invoke")

    def test_extrude_tool(self):
        """Test extrusion tool exists."""
        from slopcontrol.domains.cad.tools.cad import extrude_sketch

        assert extrude_sketch is not None

    def test_fillet_tool(self):
        """Test fillet tool exists."""
        from slopcontrol.domains.cad.tools.cad import add_fillet

        assert add_fillet is not None

    def test_boolean_tools(self):
        """Test boolean operation tools exist."""
        from slopcontrol.domains.cad.tools.cad import union_bodies, cut_body, intersect_bodies

        assert union_bodies is not None
        assert cut_body is not None
        assert intersect_bodies is not None

    def test_export_tool(self):
        """Test export tool exists."""
        from slopcontrol.domains.cad.tools.cad import export_model

        assert export_model is not None

    def test_cad_tools_list(self):
        """Test that CAD_TOOLS list contains expected tools."""
        from slopcontrol.domains.cad.tools.cad import CAD_TOOLS

        expected_tools = [
            "create_box",
            "create_cylinder",
            "create_sphere",
            "create_rect",
            "create_circle",
            "extrude_sketch",
            "add_fillet",
            "add_chamfer",
            "union_bodies",
            "cut_body",
            "intersect_bodies",
            "export_model",
        ]

        tool_names = [t.name for t in CAD_TOOLS]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"
