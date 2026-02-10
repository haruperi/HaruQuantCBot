# Branch Protection Rules

## Recommended Settings for `main` branch:

### Protect matching branches
✅ Require a pull request before merging
  - Require approvals: 1
  - Dismiss stale pull request approvals when new commits are pushed

✅ Require status checks to pass before merging
  - Require branches to be up to date before merging
  - Status checks that are required:
    - `ci-success` (from CI workflow)
    - `cpp-build (windows-latest)`
    - `cpp-build (ubuntu-latest)`
    - `python-test`
    - `static-analysis`
    - `sanitizers`

✅ Require conversation resolution before merging

✅ Require linear history

✅ Do not allow bypassing the above settings

## Setup Instructions

1. Go to: Settings → Branches → Branch protection rules
2. Click "Add rule"
3. Branch name pattern: `main`
4. Apply the settings above
5. Save changes

Repeat for `develop` branch with same settings if using GitFlow workflow.
