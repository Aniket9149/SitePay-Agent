# Engineering Change Control

Source: Roadmap Version 2.0, Part 20, and Implementation Addendum section 10.

Every significant change follows this process. A change is significant if it touches the database, agent behaviour, security, financial figures or the architecture.

## Change request fields

| Field | Content |
|-------|---------|
| Why | The problem or opportunity in plain language |
| Modules and files affected | Exact list, using the file references in the roadmap |
| Dependencies and API impact | Other modules or interfaces that change |
| Database change | Yes or no, with the migration needed |
| Agent behaviour change | Yes or no, with prompts, tools or models affected |
| Security implications | New risks and how they are controlled |
| Financial or calculation implications | Effect on any figure, rule or rounding |
| Tests required | New and existing tests, including regression evaluation |
| Acceptance criteria | How we will know it is done and correct |
| Deployment steps | How it is released |
| Rollback plan | How to undo it safely |

## Process

1. Write a change request from `docs/change_requests/change_request_template.md`.
2. Classify it. Minor: one module, no data or financial impact. Major: database, agent behaviour, security or financial impact.
3. Major changes need explicit approval from the project owner before work starts.
4. Implement on a separate branch with the required tests.
5. Run the regression evaluation (once it exists) and the rule checker.
6. Record the outcome in the decision log. Update the roadmap if scope or structure changed.

## Rules

- The architecture is frozen at the end of Phase 0 and changes only through an approved change request.
- Renaming a file listed in the roadmap needs a decision log entry first.
- Do not replace existing files or architecture without reviewing the current implementation and documenting the reason.
- Any change to a model, prompt, workflow or agent runs the regression evaluation. A worse version cannot become the production version.
