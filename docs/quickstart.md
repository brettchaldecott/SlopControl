# Quick Start Guide

## 1. Initialize a Project

```bash
slopcontrol init my-first-design
cd my-first-design
```

This creates a new project with the following structure:
```
my-first-design/
├── designs/      # Saved design states
├── exports/      # Exported CAD files
└── previews/     # Preview images
```

## 2. Start a Design Session

```bash
slopcontrol design "Create a 50mm cube with a 10mm hole through it"
```

The agent will:
1. Understand your request
2. Create the 3D model using llmcad
3. Show you a preview
4. Save the design to the project

## 3. Iterate on Your Design

When you want to make changes, just ask:

```
User: "Make it taller, 80mm instead of 50mm"
Agent: [Updates the model]
Agent: [Shows you the new preview]

User: "Add fillet to the edges"
Agent: [Adds fillet]
Agent: [Shows you the result]
```

## 4. Export Your Design

When you're happy with the design, export it:

```bash
# Export as STL (for 3D printing)
slopcontrol export cube --format stl

# Export as STEP (for CAD editing)
slopcontrol export cube --format step

# Export as GLB (for web/AR)
slopcontrol export cube --format glb
```

## 5. View Design History

Every change is automatically committed to git:

```bash
slopcontrol history
```

Output:
```
Design History:
============================================================
1. a3f8b2c | 2024-01-15 14:30
   Add fillet to edges
   by PlanForge Agent

2. b4c9d3e | 2024-01-15 14:28
   Increase height to 80mm
   by PlanForge Agent

3. c5d0e4f | 2024-01-15 14:25
   Initial cube with hole
   by PlanForge Agent
```

## Interactive Mode

Run without arguments for interactive mode:

```bash
slopcontrol design
```

You'll be prompted to enter your design request, then the agent will help you iterate.

## Design Patterns

### Mounting Plate with Holes

```
Create a 100mm x 60mm x 5mm mounting plate with 4 corner holes
```

### Cylindrical Boss

```
Create a 80mm x 80mm x 10mm base plate with a 20mm diameter
cylindrical boss in the center, raised 15mm high, with a
10mm through-hole in the middle.
```

### Hollow Box

```
Create a hollow box enclosure 50mm x 50mm x 50mm with 2mm
wall thickness.
```

## Next Steps

- [MCP Setup](mcp_setup.md) - Use PlanForge tools from AI coding assistants
- [Design Patterns](design_patterns.md) - Common CAD design patterns
