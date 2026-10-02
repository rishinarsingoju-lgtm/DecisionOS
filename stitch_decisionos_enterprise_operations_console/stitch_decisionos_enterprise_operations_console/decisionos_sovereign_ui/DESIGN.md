---
name: DecisionOS Sovereign UI
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#bec8d2'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#88929b'
  outline-variant: '#3e4850'
  surface-tint: '#89ceff'
  primary: '#89ceff'
  on-primary: '#00344d'
  primary-container: '#0ea5e9'
  on-primary-container: '#003751'
  inverse-primary: '#006591'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#c0c1ff'
  on-tertiary: '#1000a9'
  tertiary-container: '#8d90ff'
  on-tertiary-container: '#1407ad'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c9e6ff'
  primary-fixed-dim: '#89ceff'
  on-primary-fixed: '#001e2f'
  on-primary-fixed-variant: '#004c6e'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#e1e0ff'
  tertiary-fixed-dim: '#c0c1ff'
  on-tertiary-fixed: '#07006c'
  on-tertiary-fixed-variant: '#2f2ebe'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.005em
  code-metric-lg:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: -0.02em
  code-metric-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: -0.01em
  code-metric-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: 0em
  label-uppercase:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 12px
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-mobile: 0.5rem
  margin: 1rem
  margin-mobile: 0.75rem
  space-xs: 0.125rem
  space-sm: 0.25rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1rem
---

## Brand & Style
The design system is calibrated for mission-critical pharmaceutical supply chain orchestration, cold-chain integrity governance, and automated regulatory compliance. The emotional core communicates absolute operational precision, auditability, forensic transparency, and cold, deliberate authority. It explicitly rejects consumer-AI tropes—eliminating floating gradients, glowing neon orbs, conversational chatbot bubbles, and decorative synthetic animations.

The visual style is **High-Density Technical Functionalism**:
- Surface depth is communicated via subtle value shifts between dark slate layers and hairline 1px borders, reminiscent of flight-control avionics and laboratory telemetry panels.
- Information layout prioritizes scannability, parallel data visualization, status verifiability, and dense data throughput over decorative whitespace.
- Visual weight signifies real-world operational consequence: batch failure, cold-chain excursions, and distribution delays carry immediate, structured diagnostic clarity.

## Colors
The color architecture relies on a dark industrial slate canvas, preserving operator visual acuity during extended monitoring cycles while ensuring critical status indicators command instant attention.

- **Canvas & Surfaces:**
  - Base Canvas: `#0B0F19` (Deep Obsidian Slate)
  - Surface Tier 1 (Panels, Grid Cells): `#0F172A` (Slate 900)
  - Surface Tier 2 (Elevated Nodes, Inspector Drawers): `#1E293B` (Slate 800)
  - Surface Tier 3 (Hover states, Active Toolbars): `#334155` (Slate 700)
  - Structural Hairlines: `#1E293B` (Resting), `#334155` (Focused/Active)

- **Functional Data & Accent Roles:**
  - **Industrial Cyan (`#0EA5E9`):** Primary system driver, autonomous action indicators, algorithmic consensus paths, and actionable interactive controls.
  - **Emerald Green (`#10B981`):** Verified states, nominal batch temperature compliance, cryptographic audit pass, validated delivery confirmations.
  - **Amber (`#F59E0B`):** Predictive risk thresholds, supply-chain buffer degradation, ambient temperature warning zones.
  - **Crimson / Rose (`#F43F5E`):** Critical excursions, cold-chain breach, batch quarantine, immediate operator override required.
  - **Violet / Indigo (`#6366F1`):** Regulatory audit logs, FDA/EMA compliance holds, electronic batch record (eBR) verification locks.

- **Contrast Rules:** Text on any container must conform strictly to WCAG AA/AAA standards. High-contrast white (`#F8FAFC`) is reserved for critical data values, metrics, and active states; muted slate (`#94A3B8`) handles field labels and structural timestamps.

## Typography
The typography is dual-engine: **Inter** handles structural interface navigation, operational context, and prose data; **JetBrains Mono** handles all quantitative metrics, serial numbers, GTINs, batch codes, temperature readings, and audit hashes.

- **Metric Alignment:** Tabular figures (`tnum`) must be forced on all numerical layouts to ensure vertical baseline and column alignment across high-throughput data streams.
- **Label Discipline:** Micro-labels, system state indicators, and table header tags use `label-uppercase` rendered in monospace with distinct letter-spacing to establish clear hierarchy against dense numeric bodies.
- **Readability Rules:** Typography never drops below 10px. Density is achieved through reduced vertical line heights and compact horizontal margins, never through illegible scale reductions.

## Layout & Spacing
The layout follows a rigid **High-Density Operational Matrix** configured for professional multi-monitor operations, laptop workstations, and specialized warehouse tablets.

- **Grid Architecture:** 12-column or 24-column continuous fluid layout. Component containers snap directly to hairline boundaries. Gutters default to an economical `0.75rem` (12px), prioritizing immediate field-of-view data density.
- **Multi-Panel Workspace:** Default enterprise view utilizes a persistent Left Utility Strip (48px collapsed / 240px expanded), an interactive Multi-Pane Main Canvas (adaptive columns for route maps, inventory graphs, and execution queues), and a contextual Right Audit/Telemetry Rail (320px fixed).
- **Responsive Adaptations:**
  - *Desktop (>= 1440px):* Full 24-column instrumentation mode with synchronized side-by-side verification consoles.
  - *Tablet / Field Workstation (768px - 1439px):* 12-column layout; secondary telemetry drawers dock beneath primary operational controls.
  - *Mobile / Scanner Terminal (< 768px):* Single column stack; table rows convert to structured key-value diagnostic cards; critical batch overrides pin to the bottom safe zone.

## Elevation & Depth
Depth is strictly non-skeuomorphic and non-decorative. The design rejects atmospheric dropshadows, blurred glass diffusion, and heavy gradient skews in favor of **Tonal Stratification and 1px Precision Borders**.

- **Elevation 0 (Base Floor):** `#0B0F19` canvas backing the entire application.
- **Elevation 1 (Panel Tier):** `#0F172A` with a static `1px solid #1E293B` perimeter border. Zero shadow. Used for table grids, metric matrices, and continuous monitoring zones.
- **Elevation 2 (Transient Overlays & Active Nodes):** `#1E293B` bordered with `1px solid #334155`. Accompanied by a surgical shadow: `0 4px 12px rgba(0, 0, 0, 0.45)` with zero color tint. Used for context menus, flyout inspectors, and cell expansion tooltips.
- **Elevation 3 (Modal Confirmation & Critical Interventions):** `#0F172A` encased in a prominent `1px solid #64748B` border, cast against a `#020617` backdrop overlay at 80% opacity. Accompanied by `0 12px 32px rgba(0, 0, 0, 0.70)`.
- **System Focus & Active Status:** Elements gain focus through an interior or exterior 1px technical highlight in Cyan (`#0EA5E9`) or the respective status token, avoiding ambient glow rings.

## Shapes
The shape system uses a compact, disciplined **Soft Geometric (`roundedness: 1`)** specification. 

- **Containers, Cells, & Modals:** Standard corner radius is `0.25rem` (4px). This minimizes wasted corner pixel space, ensuring visual continuity along high-density tabular alignments and grid borders.
- **Status Indicators & Micro Badges:** Badges, chips, and pill indicators maintain a constrained `0.125rem` (2px) or strict `0.25rem` (4px) corner radius. Full circular pills are explicitly avoided for data badges to preserve horizontal space.
- **System Indicators:** Raw status indicators use 6px geometric squares or 6px horizontal status lines rather than soft circular dots to reflect machine-precision telemetry.

## Components

### Buttons & Trigger Controls
- **Primary Operational Button:** `#0EA5E9` background, `#0B0F19` high-contrast bold typography, 4px corner radius, padding `0.375rem 0.75rem` (6px x 12px), text `body-sm` font-weight 600. Zero drop shadow. Focus state: 1px offset ring `#38BDF8`.
- **Secondary / Technical Button:** Surface `#1E293B`, border `1px solid #334155`, text `#E2E8F0`. Hover: `#334155` background with border `#475569`.
- **Destructive / Override Button:** Surface `#4C0519`, border `1px solid #F43F5E`, text `#FECDD3`. Hover: `#E11D48` background with `#FFFFFF` text.

### Compact Status Badges
- Constructed with a tinted neutral base (`#0F172A`), a 1px border colored by the state, and monospace micro-label typography (`label-uppercase`).
- Padding: `0.125rem 0.375rem` (2px x 6px).
- Variants:
  - *Verified / Compliant:* Text `#34D399`, Border `#059669`, Background `#064E3B33` (20% opacity).
  - *Risk / Excursion Warning:* Text `#FBBF24`, Border `#D97706`, Background `#78350F33`.
  - *Quarantine / Failure:* Text `#FB7185`, Border `#E11D48`, Background `#88133733`.
  - *Regulatory Lock:* Text `#A5B4FC`, Border `#4F46E5`, Background `#312E8133`.

### Dense Data Tables
- Header row height: 28px. Cells styled with `label-uppercase` in `#64748B`, border-bottom `1px solid #1E293B`, background `#0B0F19`.
- Data row height: 32px default (or 26px compact mode). Alternating row striping is avoided; differentiation relies strictly on horizontal 1px divider lines (`#1E293B`) and hover cell illumination (`#1E293B4D`).
- Numerical columns right-align with `code-metric-md`. Critical status indicators display left-aligned inline badges with monospace transaction hashes.

### Form Inputs & Telemetry Filters
- Field height: 28px. Background: `#0B0F19`, Border: `1px solid #334155`, Text: `#F8FAFC` in `body-sm`.
- Padding: `0.25rem 0.5rem`.
- Focus state: Border transitions to `#0EA5E9`; no outer glow ring.
- Checkboxes and Radio controls are strict 14px geometric units with sharp, clear contrast ticks, ensuring distinct legibility on touch terminals or low-gamma monitors.

### Specialized Supply-Chain Components
- **Audit Verification Rail:** Dedicated log listing cryptographic block IDs, timestamps, and model inference confidence scores (e.g., `CONF: 99.82%`) using `JetBrains Mono` at `code-metric-sm`.
- **Cold-Chain Telemetry Card:** Compact container featuring a dual-axis micro-sparkline, real-time threshold markers (min/max limits in dashed `#64748B`), and instantaneous status indicators.
- **Autonomous Action Queue Item:** Modular alert row displaying recommended action, algorithm confidence score, impact radius, and single-click manual override / confirmation triggers.