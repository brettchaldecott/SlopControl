---
name: Ducted Fan Assembly
domain: cad
version: "1.3"
status: verified
created: "2026-04-23T10:00:00+00:00"
tags: [ducted-fan, brushless-motor, 3d-printed, petg-cf]
agents: [slopcontrol-cad]
---

# Requirements
- Thrust ≥ 2.0 kg at 60% throttle
- Outer diameter: 90mm (fits standard EDF housing)
- Material: PETG-CF or Nylon-CF, FDM 0.4mm nozzle
- Motor: Custom wound, 12N14P, Kv ~ 1200
- Max overhang angle for 3D printing: 45°

# Design Decisions

## 1. Propulsion Architecture
- **Decision:** Direct drive, no gearbox
- **Rationale:** Weight saving (18g) and 8% efficiency gain at cruise
- **Consequence:** Higher Kv motor required; see thermal analysis in Appendix B
- **KB Link:** [[Gearbox vs Direct Drive Trade Study]]

## 2. Motor Design
- **Decision:** 12N14P configuration, delta winding
- **Rationale:** Maximises copper fill in Ø22mm stator; matches [KB: Motor Winding Patterns]
- **Parameters:**
  - Stator: Ø22mm x 10mm stack, 0.2mm laminations
  - Winding: Δ (delta), 0.45mm wire, 9 turns per tooth
  - Magnets: 14x N52, 2mm arc segments, 1.0mm air gap
- **Script:** [generated/motor_stator.py](generated/motor_stator.py)

## 3. Impeller / Duct
- **Decision:** 5-blade Clark-Y profile with 12° root → 35° tip twist
- **Rationale:** Compromise between efficiency at cruise and stall margin
- **Parameters:**
  - Blades: 5, Clark-Y profile
  - Hub: Ø12mm, integrates motor rotor bell
  - Shroud: 1.5mm wall, 0.5mm blade tip clearance
- **Script:** [generated/impeller_assembly.py](generated/impeller_assembly.py)

## 4. Mounting System
- **Decision:** Front 4x M3 inserts + rear integrated motor backplate
- **Rationale:** Vibration isolation via 2mm TPU gasket
- **Risk:** Resonance mode at 180 Hz, see Appendix B vibration analysis

# Implementation Steps
1. Generate motor stator geometry (slopcontrol generate --domain cad --section motor)
2. Generate impeller blade profile and hub (slopcontrol generate --domain cad --section impeller)
3. Generate shroud/duct housing
4. Assembly: motor + impeller → verify clearances
5. Export STEP for FEA thermal analysis
6. Generate supports for 3D printability check

# Verification Log
| Version | Check | Result | Notes |
|---|---|---|---|
| 1.0 | Mesh | FAIL | Planet gear interfered with ring (wrong ratio) |
| 1.1 | Mesh | PASS | Reduced planet OD by 0.4mm |
| 1.2 | Printability | FAIL | 0.6mm wall delaminated in PETG-CF |
| 1.3 | Printability | PASS | Walls increased to 1.2mm |
| 1.3 | Structural | PASS | 6.2x safety factor at max thrust (FEA) |
| 1.3 | Thermal | PASS | 78°C max winding temp at 80% throttle |

# Appendices

## Appendix A: Gearbox vs Direct Drive Trade Study
Detailed comparison table: weight, efficiency, complexity, cost.
Direct drive won because the weight penalty of a 3D-printed gearbox (18g)
exceeded the expected efficiency gains at our target cruise point.

## Appendix B: Vibration and Thermal Analysis
Modal analysis shows first bending mode at 178 Hz.
Thermal FEA: 78°C winding, 62°C magnet under continuous 80% throttle.

## Appendix C: Winding Calculation and Kv Prediction
Turns: 9, wire: 0.45mm, delta connection.
Predicted Kv: 1180 RPM/V (measured: 1195 RPM/V).
