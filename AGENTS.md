# Frontend Design Workflow

For frontend design/refinement:

1. Use `design-taste-frontend` to establish visual quality and avoid generic template-like design.

2. Use `design-system-reference` as the project's selected visual-system reference.

3. After implementation, use `web-design-guidelines` as the audit/review pass.

Do not let the three skills conflict randomly.

Preferred workflow:

Design Taste
→ Selected Design System
→ Web Design Guidelines Audit

# Project Visual Direction

The frontend should feel like:

"a polished internal CPU/microarchitecture verification tool suitable for a public engineering demo"

Avoid:
- generic AI dashboard styling
- purple/blue glow gradients
- neon hacker UI
- glassmorphism
- oversized marketing heroes
- cartoon CPU imagery
- unnecessary animation
- fake terminals
- fake waveforms

Prefer:
- technical clarity
- dense but readable information
- compact controls
- clear verification states
- real data
- neutral dark or light engineering palette
- restrained blue/cyan accent
- green only for PASS
- red only for real FAIL
- amber for warning / deliberate fault injection
- monospace for traces, addresses, counters, and hardware values

# Execution Rule

Unless explicitly asked by the user:
- do not run project builds
- do not run npm
- do not run dev servers
- do not run Python
- do not run FastAPI
- do not run iverilog
- do not run vvp
- do not run tests

Make source changes and stop for manual validation.
