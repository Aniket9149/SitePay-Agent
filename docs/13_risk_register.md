# Risk Register

Source: Roadmap Version 2.0, Part 24, plus risks found during the build. Impact and likelihood are judgments by the builder and should be reviewed by the owner.

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Local language voice is misunderstood | Wrong facts | Transcript correction, ask on low confidence, learn from corrections | Planned |
| Quantity estimated wrongly from photos | Wrong claim | Photos are proof, quantity comes from measurements and drawings through code | Planned |
| A wrong claim damages client trust | Lost customer | Mandatory approval, evidence on every line, final checklist | Planned |
| Rules or tax applied incorrectly | Wrong payment | Expert confirmation, versioned packs, review note on every claim | Planned |
| Users do not want to learn software | No adoption | Very simple screens, voice first, three taps or fewer | Planned |
| Too many features too early | Delay | Phase gates, strict focus on first release | Active |
| Data leak | Severe | Tenant separation, encryption, security review | Planned |
| Model costs grow | Margin loss | Smaller images, caching, usage limits | Planned |
| Solo builder overload | Delay | Small phases, daily routine, early help from pilot users | Active |
| Building before validating the need | Wasted months | Validation Gate in Phase 0 | **Active: gate not passed** |
| A calculation error causes a wrong payment | Severe | Isolated engine, decimals, traces, full tests | Planned |
| The agent gives a legal opinion | Legal exposure | Entitlement flags only, source clauses, AI use disclaimer | Planned |
| Field data lost offline | Severe | Durable queue, idempotent uploads, visible sync status | Planned |
| A model change quietly lowers quality | Silent errors | Regression gate and model registry | Planned |
| Uncontrolled change breaks the plan | Rework | Change control, architecture freeze | Active |
| Provider outage or price change | Downtime | Fallback policy, single model client | Planned |
| Build sandbox cannot run the planned stack (D-003) | Untestable code | Do not mark untested code as tested, get packages installed or test on owner machine | **Active** |
| Foundation built before scope freeze (D-002) | Rework | Keep Phase 1 generic, no scope expansion | **Active** |
| Work exists only in the sandbox, not in GitHub (D-007) | Total loss of work | Checkpoint ZIPs, local Git repository, owner to create or share the repository | **Active** |
| Phase 1 code never executed against a database (D-003) | Hidden defects, for example SQLite savepoint behaviour | Run the 12 integration tests first in a full environment | **Active** |
| No login rate limiting yet | Password guessing | Add rate limiting and lockout before any pilot | **Active** |
| Approval roles are a default, not a decision | Wrong people approve claims | Owner decides, then change request | **Active** |
