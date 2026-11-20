# Concept

Source: Roadmap Version 2.0, Part 1.

## What it is

SitePay Agent is a vertical, multimodal AI agent for construction project management. It reads site photos, voice notes, drawings, bills and project documents, compares actual work with planned work, flags missing or inconsistent information, and prepares progress reports and payment claim documents.

## Vision

Make construction work more transparent, efficient and easier to manage for everyone involved, from small building projects to large infrastructure developments, in any country.

## The problem

Information is lost between workers, engineers, contractors and office teams. Photos sit in messaging apps, measurements sit in notebooks and bills sit in separate folders. Preparing a payment claim takes hours, errors are common, clients reject incomplete claims, and payment is delayed by weeks or months. Small contractors rarely have a documentation team or the budget for enterprise software.

## The solution

An agent that bridges the site and the office. It collects evidence, links it to measurements and documents, checks it against the plan, and moves the work toward a payment claim. It says what is missing, what does not match and what to do next.

## What makes it different

It is not a chatbot and not a report generator. It ties every claim to proof and connects directly to time, money and productivity.

## What it is not

Not a general assistant, not a full enterprise resource planning system, and not an autonomous payer. Final approval always stays with a qualified human.

## Core loop

1. Site evidence arrives.
2. The agent reads it and extracts quantities.
3. It compares them with the plan.
4. It flags mismatches, missing documents, delays and duplicate bills.
5. A person reviews and confirms.
6. The agent drafts the progress report and payment claim.
7. After approval the claim is submitted.
8. Payment status is tracked.

## Worked example

A site engineer uploads three photos of finished plaster, a voice note saying the east wall of the third floor is complete, and a measurement sheet. The agent identifies the wall, understands the location and work type from the voice note, calculates the area from the drawing in code, matches it to the correct Bill of Quantities item, checks the area was not claimed in an earlier bill, and drafts the claim line. If the voice note says complete but a photo shows an unfinished section, it raises a flag and asks the engineer to confirm before anything is claimed.

## First release scope

In scope and out of scope lists are kept in the roadmap, Part 3. They are frozen only when the Product Validation Gate passes (see `docs/21_product_validation_gate.md`).
