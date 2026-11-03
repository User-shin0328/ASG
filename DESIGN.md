---
name: ASG DB Access Dashboard
description: A Korean operating dashboard for database-read review, measured status, and persistent request reports.
colors:
  ground: "#101313"
  surface: "#151a19"
  raised: "#1c2422"
  ink: "#f2f6f5"
  muted: "#a7b6b1"
  line: "#2b4440"
  accent: "#68d0c1"
  green: "#72cda2"
  red: "#f29b9b"
  amber: "#e6c384"
  control-stroke: "#4a6860"
  danger-stroke: "#926362"
  error-stroke: "#a97772"
  selection: "#316e63"
  bar-track: "#25332f"
  chart-grid: "#30403c"
  unknown-status: "#8d9c98"
  dialog-stroke: "#56776e"
typography:
  title:
    fontFamily: '"Segoe UI", "Malgun Gothic", sans-serif'
    fontSize: "26px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.02em"
  section:
    fontFamily: '"Segoe UI", "Malgun Gothic", sans-serif'
    fontSize: "16px"
    fontWeight: 600
  subheading:
    fontFamily: '"Segoe UI", "Malgun Gothic", sans-serif'
    fontSize: "14px"
    fontWeight: 600
  body:
    fontFamily: '"Segoe UI", "Malgun Gothic", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  table:
    fontFamily: '"Segoe UI", "Malgun Gothic", sans-serif'
    fontSize: "13px"
    fontWeight: 400
  label:
    fontFamily: '"Segoe UI", "Malgun Gothic", sans-serif'
    fontSize: "12px"
    fontWeight: 400
  metric:
    fontFamily: '"Segoe UI", "Malgun Gothic", sans-serif'
    fontSize: "28px"
    fontWeight: 400
    lineHeight: 1.2
  risk-score:
    fontFamily: '"Segoe UI", "Malgun Gothic", sans-serif'
    fontSize: "32px"
    fontWeight: 500
    lineHeight: 1.2
  identifier:
    fontFamily: "Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  bar: "2px"
  control: "6px"
  surface: "10px"
  dialog: "12px"
  status-dot: "50%"
spacing:
  small: "8px"
  compact: "12px"
  group: "16px"
  grid: "18px"
  panel: "20px"
  section: "24px"
  sidebar-top: "30px"
  page-inline: "32px"
components:
  button-secondary:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-primary:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-danger:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  input:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 11px"
  sidebar:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    padding: "30px 20px 20px"
    width: "216px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "20px"
  report-dialog:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.dialog}"
    width: "min(860px, calc(100vw - 40px))"
---

# Design System: ASG DB Access Dashboard

## Overview

**Creative North Star: "Data terminal"**

The ASG dashboard is a Korean operating surface for reviewing structured database-read requests. The confirmed brief uses neutral dark backgrounds, near-white text, thin teal separation, a left sidebar, and separate overview, approval, audit, and test pages. Charts and measured component states supply the overview; the former request-path diagram is no longer part of the composition.

The Data terminal direction in `.taste-skill/direction.json` (seed `994061310`) remains a reference for restrained density and scanability. The user-approved evolution takes precedence over its generic palette, icon rail, font recommendations, and one-pixel-only accent budget. Offline Korean typography, reason-based review, and explicit status language shape the implemented system.

**Key Characteristics:**

- A persistent labelled sidebar that becomes a mobile drawer.
- Flat bordered surfaces, teal separators, and near-white reading text.
- Real request outcomes, a scaled 30-minute trend, and measured component states.
- A focused request report with required reviewer reasoning.

## Colors

Teal structures the dark neutral interface; green, red, and amber carry specific operational states.

### Primary

- **Teal accent:** Selected navigation edges, control focus and hover borders, primary action outlines, allowed states, outcome bars, and the operational-risk line.
- **Teal line:** Structural panel borders, sidebar edge, header separators, table rows, and report divisions.

### Neutral

- **Ground, surface, raised:** Page/control background, flat task containers, and hover feedback respectively.
- **Ink and muted:** Main reading text and subordinate labels, evidence metadata, placeholders, and chart captions.
- **Control stroke:** The stronger outline of editable fields and default buttons.
- **Bar track and chart grid:** Quiet data context behind the colored marks.
- **Unknown status:** Unmeasured or unavailable status; do not paint uncertainty green.

### Semantic states

- **Green:** A component actually reported as operating normally.
- **Red:** Failed component connectivity, blocked outcomes, rejected/expired requests, and report errors.
- **Amber:** Pending outcomes and high/critical request-risk text.
- **Danger stroke and error stroke:** Rejection-action and error-notice boundaries.
- **Selection and dialog stroke:** Readable selected text and the focused report container.

**The Thin Separation Rule.** Structural borders and selected navigation edges are one pixel. Data marks retain their implemented geometry: six-pixel outcome bars, a two-pixel risk line, and eight-pixel status dots. Keyboard focus uses a two-pixel teal outline with a four-pixel offset.

**The Measured State Rule.** Show green or red component dots only with an actual status response and explicit words such as normal or connection failure. Unknown state remains neutral.

## Typography

**Title and body font:** Segoe UI, with Malgun Gothic and sans-serif fallbacks.
**Identifier font:** Consolas, with monospace fallback, for request IDs, trace IDs, and approval hashes only.

Use installed fonts so the local Korean interface works without downloads. Dates, times, counts, risk values, table rows, JSON-formatted filter descriptions, and report prose use the body family. Numeric measures use tabular figures.

### Hierarchy

- **Title:** Page heading, reduced to 23px at the mobile breakpoint.
- **Section:** Chart, table, and task headings; mobile section headings may reduce to 15px.
- **Subheading:** Report sections and diagnostic checks.
- **Body:** Base reading text and controls.
- **Table:** Table cells, supporting prose, and report fields.
- **Label:** Form labels, status words, table headings, and footnotes.
- **Metric:** Request counts; the compact desktop size is 26px and mobile size is 27px.
- **Risk score:** The current operational indicator, distinct from an individual request's analysis.
- **Identifier:** Technical trace and binding evidence kept behind details where appropriate.

The report dialog title is 19px, reduced to 17px on mobile. Decision text uses 14px, decision buttons are at least 44px tall, and mobile review inputs use 16px. Small chart-axis labels and selected metadata remain 11px in the observed desktop implementation.

## Layout

A fixed left sidebar is 216px wide, with a one-pixel separating edge and environment details at the bottom. The main region starts after that sidebar, uses 30px top and 32px horizontal padding, and has a maximum width of 2000px. Above 1800px, its horizontal padding becomes 48px. Each route has a shared page header, refresh action, feedback area, and footer.

The overview begins with a three-column chart/status row in 1.2:1.2:0.85 proportions, with the last column at least 210px wide. The row uses 18px gaps and chart panels have a 270px minimum height. A shared four-column request-count panel and a recent-history table follow. Panels use 20px padding.

At 1150px and below, the sidebar narrows to 188px and main padding becomes 26px by 24px. Outcome and trend charts share two columns; the status region spans both columns with four status cells. Diagnostic content becomes one column.

At 760px and below, the sidebar becomes a 216px drawer opened by a visible menu button; main content removes the sidebar offset and starts at 82px top padding with 20px side padding. Charts stack with 16px gaps, status becomes two columns, and request metrics become a two-by-two grid. Panels use 18px padding. Toolbars stack, fields share available width, and diagnostic/demo actions expand to full width.

Mobile tables become labelled-by-context record layouts rather than compressed desktop grids: request time, requester/target, state or risk, requested scope, and report action remain available. Table headings are visually removed; each row is a two-column grid with wrapped content and a minimum 40px action. Desktop tables retain a contained horizontal overflow region.

The report dialog is at most 720px wide and 90vh tall with internal scrolling. Its header stays visible. Two-column evidence fields become one column on mobile; report action buttons share the available width. Diagnostic introduction copy has a maximum measure of 66ch.

## Elevation & Depth

Surfaces are flat and have no shadows, decorative glow, glass, or gradients. One-pixel teal-toned outlines and tonal differences define containers. The report dialog uses a dark translucent backdrop to create protected review focus; the mobile drawer also remains shadow-free.

**The Flat Evidence Rule.** Separate evidence with spacing, type hierarchy, and thin rules. Reserve the dialog backdrop for focused request review, not general decoration.

## Shapes

Panels use the surface corner radius; controls use the smaller control radius. The report dialog has its own slightly softer corners. Outcome tracks use small corners, and component status dots are circular. Results and risk labels remain plain text rather than filled pills.

## Components

### Sidebar Navigation

Four labelled routes are implemented: `/`, `/approvals`, `/audit`, and `/tests`. Consistent outline SVG icons accompany text. Active navigation has near-white text and a thin teal bottom edge; hover uses the raised neutral background. The pending count is aligned to the right. Mobile navigation preserves the same labels in the menu-controlled drawer.

### Buttons

Default, primary, and rejection controls share compact outlined geometry and a 38px minimum height. Primary uses a teal border; rejection uses the danger stroke. Hover raises the neutral background and highlights the border in teal. Disabled actions reduce opacity and show a wait cursor. Table actions have a 32px desktop minimum and a 40px mobile minimum.

### Inputs / Fields

Ground-filled fields use a distinct control stroke, teal caret, muted placeholders, and shared keyboard focus. Audit dates are explicitly in Korean time. Approval and rejection require a reviewer reason between three and 1,000 characters. Invalid or failed decisions expose an inline report alert.

### Panels and Rows

Task regions use one-pixel teal-toned boundaries and flat surface fill. Outcome, risk, and status panels carry real data. Shared metric counts use internal dividers rather than separate raised cards. Audit and approval rows show state, scope, and a report action; lists expose sorting, pagination, and explicit empty states.

### Outcome and Risk Charts

The overview's outcome bars show today's pending, allowed, and blocked request counts. Bar lengths use the day's total as the denominator, and labels show exact counts. Blocked includes automatic policy denial, reviewer rejection, and expiry.

The operational-risk chart covers the last 30 minutes, has a visible 0–100 scale and 30-minutes-ago, 15-minutes-ago, and current labels, and uses the actual returned trend. Sensitive, bulk, and abnormal factor counts accompany it. The current indicator and individual request risk are distinct measures.

### Component Status

Gateway, security analysis, protected DB, and audit DB status are measured by actual connectivity or analysis self-checks. Green means normal, red means failed, and neutral means unknown. Words accompany every dot. Diagnostic checks show explicit pass/fail text and their scope.

### Request Report and Review

A native dialog provides protected focus for request review. It shows when, who, gateway-observed source IP, tenant/task, database/dataset, requested columns, row limit, filters, purpose, explainable analysis, recommendation, and processing history. Pending requests add reason-based approval/rejection; completed decisions show reviewer and outcome. Trace and approval hashes remain under a native disclosure.

Explicit policy can authorize routine structured DB reads automatically. Other valid requests require human review; policy violations remain blocked. A reviewer can issue one-time authorization or a scoped grant bounded by duration, calls, and total rows. The originating agent separately asks to execute the read. Reports display metadata and processing evidence, not the returned business rows. Approval review also lists scoped grants with reason-based revocation and principal query budgets.

### Feedback and Motion

Loading, empty lists, token-required state, connection failures, diagnostic outcomes, and stale displayed information have explicit text. Refresh runs at ten-second intervals when the tab and connection state permit it. Counts carry an as-of timestamp and Asia/Seoul day scope.

Button background transitions last 160ms; the mobile drawer transform uses 180ms ease. Reduced-motion preference disables transitions and smooth scrolling. Preserve visible keyboard focus, skip navigation, native dialog behavior, labelled inputs, and selection/caret treatments.

## Do's and Don'ts

### Do:

- **Do** preserve the neutral dark palette, near-white text, and thin teal separation.
- **Do** use green and red for measured component status with explicit status words.
- **Do** retain the offline Korean font stack and tabular numerals for counts and times.
- **Do** show the metric as-of time and Korean-time scope alongside request counts.
- **Do** preserve report evidence, required reviewer reasons, and the distinction between approval and execution.
- **Do** transform table rows into readable mobile records while keeping the report action visible.

### Don't:

- **Don't** restore the request-path diagram or replace the sidebar with the generic direction's icon rail.
- **Don't** use mono for ordinary Korean labels, request counts, dates, times, or report prose.
- **Don't** add decorative shadows, glows, gradients, or large colored status panels.
- **Don't** imply that the operational risk score is an LLM probability or a breach probability.
- **Don't** present fictional validation records as a connected corporate production database.
