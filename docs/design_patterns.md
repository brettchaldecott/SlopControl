# Design Patterns

This guide covers common CAD design patterns and how to implement them with PlanForge.

## 1. Mounting Plate with Holes

A flat plate with corner mounting holes for bolts.

### Description
- Base plate with specified dimensions
- Four holes positioned at corners
- Holes inset from edges for clearance
- Optional fillet on top edges

### Design Request
```
Create a 100mm x 60mm x 5mm mounting plate with 4 corner holes.
The holes should be 5mm in diameter and inset 8mm from each corner.
Add a 2mm fillet to the top edges.
```

### Implementation Pattern
```python
# 1. Create base plate
plate = Box(100, 60, 5)

# 2. Add corner holes using face corners
# 3. Fillet top edges
```

## 2. Cylindrical Boss

A raised cylinder on a flat surface with a through-hole.

### Description
- Flat base plate
- Cylindrical boss raised from surface
- Central hole through the boss
- Often used for bearing seats or screw mounts

### Design Request
```
Create an 80mm x 80mm x 10mm base plate with a 25mm diameter
cylindrical boss in the center, raised 20mm high. Add a 12mm
through-hole in the center of the boss.
```

## 3. Hollow Box / Enclosure

A thin-walled hollow container.

### Description
- Outer box with specified wall thickness
- Single opening (typically top face removed)
- Interior hollow
- Used for enclosures, cases, containers

### Design Request
```
Create a hollow box 60mm x 40mm x 30mm with 2mm wall thickness.
```

### Implementation Pattern
```python
# 1. Create solid outer box
outer = Box(width, height, depth)

# 2. Shell out using top face
# Note: llmcad shell operation removes material
result = shell(outer.top, thickness=wall_thickness)
```

## 4. L-Bracket

An L-shaped bracket for corner mounting.

### Design Request
```
Create an L-bracket with a 60mm x 40mm vertical face and a
100mm x 40mm horizontal base. Both faces should be 5mm thick.
Add 4mm mounting holes in the base and 3mm mounting holes
in the vertical face.
```

## 5. Flanged Part

A cylindrical part with a flat mounting flange.

### Design Request
```
Create a flanged part with a 20mm diameter shaft 40mm long
and a 40mm diameter flange 5mm thick at the base.
```

## 6. Stepped Shaft

A shaft with multiple diameter sections.

### Design Request
```
Create a stepped shaft with three sections:
- Bottom: 30mm diameter, 20mm long
- Middle: 20mm diameter, 30mm long
- Top: 15mm diameter, 20mm long
```

## 7. Interlocking Parts

Two parts designed to fit together.

### Design Request
```
Create a male and female interlocking bracket:
- Male part: 40mm cube with a 10mm x 10mm tongue
- Female part: 45mm cube with a 10mm x 10mm slot
```

## 8. Ribbed Panel

A flat panel with reinforcing ribs on the back.

### Design Request
```
Create a 100mm x 80mm x 5mm panel with 4 rectangular ribs
on the back side, running vertically. The ribs should be
5mm wide and 8mm tall.
```

## 9. Chamfered Box

A box with chamfered (beveled) edges for aesthetics or safety.

### Design Request
```
Create a 40mm cube with chamfered edges. All edges should
have a 2mm chamfer.
```

## 10. Custom Profile Extrusion

A profile created by extruding a custom 2D sketch.

### Design Request
```
Create a T-slot aluminum style extrusion, 20mm wide and
with the T-slot being 6mm wide and 10mm deep.
```

## Design Best Practices

### 1. Start Simple
Begin with basic shapes that capture the overall form. Add features incrementally.

### 2. Use Named Faces
llmcad provides named faces (`top`, `bottom`, `front`, `back`, `left`, `right`). Use these for positioning instead of coordinates.

### 3. Think in Operations
- **Union (+)**: Combine shapes
- **Cut (-)**: Remove material
- **Intersect (&)**: Keep overlap

### 4. Verify Often
Request previews after major operations to catch issues early.

### 5. Use Appropriate Tolerances
- For 3D printing: 0.1-0.2mm clearance
- For CNC machining: 0.05-0.1mm clearance
- For assembly: Consider worst-case tolerances

## Common Dimensions

| Application | Typical Values |
|-------------|----------------|
| M3 screw clearance | 3.2-3.4mm hole |
| M4 screw clearance | 4.2-4.4mm hole |
| M5 screw clearance | 5.2-5.4mm hole |
| Press fit bearings | Hole = OD - 0.05mm |
| Snap fits | Deflection 1-2mm |
| Fillet radius | 0.5-2x wall thickness |
