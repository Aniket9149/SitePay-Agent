# Uploading SitePay Agent to GitHub

Status on 2026-11-22: **uploaded and executed in CI.** Branch `sp-01/architect-foundation` is on GitHub (`Aniket9149/SitePay-Agent`). This file is kept for anyone setting up another copy.
Never paste tokens or passwords into a chat. Use the steps below on your own computer, where Git asks you to sign in itself.

## Option A: from the ZIP (works today)

1. Create an empty repository named `SitePay-Agent` under your account on github.com. Do not add a README or license there.
2. Unzip `sitepay-agent_checkpoint_*.zip`. If the ZIP contains a `.git` folder, you already have the history: skip to step 4.
3. In the unzipped `sitepay-agent` folder:
   ```
   git init
   git checkout -b sp-01/architect-foundation
   git add .
   git commit -m "SP-01: Phase 0 and Phase 1 backend foundation, shared contracts"
   ```
4. Connect and push the branch (never `main`, never force):
   ```
   git remote add origin https://github.com/Aniket9149/SitePay-Agent.git
   git push -u origin sp-01/architect-foundation
   ```
5. Check on github.com that the branch and files are there. Open a pull request into `main` and review it before merging.

## Option B: let the build session push

Create the repository and make it available to the session in your Claude connection settings for GitHub. Then ask the session to push
branch `sp-01/architect-foundation`. It will first check what already exists in the repository, so other agents' work is not overwritten.

## If the repository already has files from other workstreams

Do not overwrite. Fetch first (`git fetch origin`), compare, and merge on a branch. Migrations must stay one linear chain.

## After upload

Install dependencies and run the tests. The 15 integration tests are the Phase 1 exit check:
```
pip install -e ".[dev]"
python -m pytest tests backend/tests -rs
```
