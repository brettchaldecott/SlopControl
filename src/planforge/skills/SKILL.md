---
name: cad-design
description: Design and create 3D CAD models using natural language.
             Use when user wants to create, modify, or iterate on 3D parts.
license: MIT
compatibility: Python 3.10+
allowed_tools:
  - create_box
  - create_cylinder
  - create_sphere
  - create_rect
  - create_circle
  - create_polygon
  - extrude_sketch
  - add_fillet
  - add_chamfer
  - union_bodies
  - cut_body
  - intersect_bodies
  - export_model
  - render_preview
---

# CAD Design Skill

## When to Use
- User wants to create a new 3D part
- User wants to modify an existing design
- User wants to iterate on a design until correct
- User wants to export a design for manufacturing/printing

## Workflow

### Phase 1: Understand the Request
1. Clarify any ambiguous requirements
2. Note specific dimensions mentioned
3. Identify intended use (3D printing, CNC, visual prototype)

### Phase 2: Plan the Design
Use `write_todos` to break down the work:
```
□ Create base geometry
□ Add mounting holes (if applicable)
□ Add features (bosses, slots, etc.)
□ Apply finishing operations (fillet, chamfer)
□ Export final design
```

### Phase 3: Build Incrementally
1. Create simple base shape
2. Add features one at a time
3. Call `render_preview` after each major change
4. Verify with user before proceeding

### Phase 4: Refine Based on Feedback
- "Make it taller" → modify extrusion amount
- "Round the corners" → add fillet
- "Add holes" → use cut operation with circle sketch

### Phase 5: Export
- STEP for editing in CAD software
- STL for 3D printing
- GLB for web/AR viewing

## Common Patterns

### Pattern: Mounting Plate with Holes
```
1. Box(100, 60, 5) → plate
2. For each corner in plate.top.corners:
     inset(8, 8) → position
     Circle(5) → hole sketch
     extrude(through=True) → cut
3. fillet(plate.top.edges, 2)
```

### Pattern: Cylindrical Boss
```
1. Box(80, 80, 10) → base
2. Circle(20) on base.top → boss_sketch
3. extrude(boss_sketch, 15) → boss
4. union(base, boss) → result
5. Circle(10) on result.top → hole_sketch
6. extrude(hole_sketch, through=True) → cut
```

### Pattern: Hollow Box
```
1. Box(50, 50, 50) → outer
2. Add all features (holes, etc.)
3. shell(outer.top, 2) → hollow
```

## Tips
- Start with 2-3 main dimensions, add details later
- Use `get_body_info` to verify dimensions
- Prefer STEP export for editable files
- Small fillets first (2-3mm), large ones last
- If fillet fails, try chamfer instead

## Limitations
- Complex organic shapes are difficult (use mesh tools for those)
- Imported geometry support is limited
- Some CAD operations may fail; try alternative approaches
