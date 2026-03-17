#!/usr/bin/env bash
# Checks open PRs and issues on loughmiller/connect-four and takes action:
# - Merges approved PRs with passing checks
# - Uses Claude Code to address unaddressed PR review comments
# - Uses Claude Code to work on open GitHub issues
#
# Intended to be run via cron or CI, outside of a live Claude session.

set -euo pipefail

REPO="loughmiller/connect-four"

# Load secrets directly from secrets.json
SECRETS_FILE="/workspace/secrets.json"
if [ -f "$SECRETS_FILE" ]; then
    eval "$(python3 -c "
import json
with open('$SECRETS_FILE') as f:
    for k, v in json.load(f).items():
        print(f'export {k}=\"{v}\"')
")"
fi

# Verify gh can reach the API
if ! gh api "repos/${REPO}" --jq '.full_name' &>/dev/null; then
    echo "Error: gh CLI cannot access ${REPO}. Check GITHUB_TOKEN or run 'gh auth login'."
    exit 1
fi

# Verify claude is available
if ! command -v claude &>/dev/null; then
    echo "Error: claude CLI is not installed."
    exit 1
fi

cd /workspace

# Ensure we're on main and up to date before doing anything
git checkout main && git pull

# ============================================================
# Part 1: Handle open PRs
# ============================================================

prs=$(gh api "repos/${REPO}/pulls" --jq '.[].number')

for pr_number in $prs; do
    echo "=== Checking PR #${pr_number} ==="

    # Get PR details
    pr_json=$(gh api "repos/${REPO}/pulls/${pr_number}")
    pr_branch=$(echo "$pr_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['ref'])")
    pr_head_sha=$(echo "$pr_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

    # Check reviews
    reviews=$(gh api "repos/${REPO}/pulls/${pr_number}/reviews")
    approved=$(echo "$reviews" | python3 -c "import sys,json; print(len([r for r in json.load(sys.stdin) if r['state']=='APPROVED']))")

    # Check CI status
    checks_pass=true
    check_state=$(gh api "repos/${REPO}/commits/${pr_head_sha}/status" --jq '.state' 2>/dev/null || echo "unknown")
    if [ "$check_state" = "failure" ] || [ "$check_state" = "error" ]; then
        checks_pass=false
    fi

    # If approved and checks pass, merge
    if [ "$approved" -gt 0 ] && [ "$checks_pass" = true ]; then
        echo "PR #${pr_number} is approved with passing checks. Merging..."
        gh api "repos/${REPO}/pulls/${pr_number}/merge" -X PUT -f merge_method=squash
        git checkout main && git pull
        git branch -d "${pr_branch}" 2>/dev/null || true
        echo "PR #${pr_number} merged and local branch cleaned up."
        continue
    fi

    # Gather all feedback on the PR
    review_comments=$(gh api "repos/${REPO}/pulls/${pr_number}/comments")
    issue_comments=$(gh api "repos/${REPO}/issues/${pr_number}/comments")

    review_comment_count=$(echo "$review_comments" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
    issue_comment_count=$(echo "$issue_comments" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
    review_body_count=$(echo "$reviews" | python3 -c "import sys,json; print(len([r for r in json.load(sys.stdin) if r['body'].strip()]))")

    total=$((review_comment_count + issue_comment_count + review_body_count))
    if [ "$total" -eq 0 ]; then
        echo "PR #${pr_number}: no comments to address."
        continue
    fi

    echo "PR #${pr_number} has feedback: ${review_body_count} review(s) with body, ${review_comment_count} inline comment(s), ${issue_comment_count} issue comment(s)."
    echo "Checking out branch and invoking Claude to address them..."

    # Check out the PR branch
    git fetch origin "${pr_branch}"
    git checkout "${pr_branch}"
    git pull origin "${pr_branch}"

    # Build the prompt for Claude
    prompt="You are working on PR #${pr_number} on the ${pr_branch} branch of ${REPO}.

Here are the reviews (with state and body) on this PR:
${reviews}

Here are the inline review comments on this PR:
${review_comments}

Here are the issue/conversation comments on this PR:
${issue_comments}

For each piece of unaddressed feedback:
- If the feedback requests a change and you agree, implement it, run tests (pytest --cov --cov-fail-under=100), commit, and push to the ${pr_branch} branch.
- If the feedback requests a change and you disagree, reply to the comment via the gh API explaining your reasoning and ask for clarification before making changes.
- If the feedback is a question (not a change request), reply to the comment via the gh API with a helpful answer.

After addressing all feedback, run tests one final time to make sure everything passes.
Never push directly to main. Only push to the ${pr_branch} branch."

    # Run Claude in non-interactive mode to address the comments
    echo "$prompt" | claude --print --dangerously-skip-permissions

    # Return to main
    git checkout main
    echo "PR #${pr_number}: done processing comments."
done

# ============================================================
# Part 2: Handle open issues (that don't already have a PR)
# ============================================================

# Get open issue numbers, excluding pull requests (GitHub treats PRs as issues)
issues=$(gh api "repos/${REPO}/issues" --jq '[.[] | select(.pull_request == null)] | .[].number')

# Get open PR branches so we can skip issues that already have work in progress
pr_branches=$(gh api "repos/${REPO}/pulls" --jq '.[].head.ref')

for issue_number in $issues; do
    echo "=== Checking issue #${issue_number} ==="

    issue_json=$(gh api "repos/${REPO}/issues/${issue_number}")
    issue_title=$(echo "$issue_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['title'])")
    issue_body=$(echo "$issue_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('body') or '')")
    issue_labels=$(echo "$issue_json" | python3 -c "import sys,json; print(','.join(l['name'] for l in json.load(sys.stdin).get('labels', [])))")
    issue_comments=$(gh api "repos/${REPO}/issues/${issue_number}/comments")

    # Skip issues with a "wontfix" or "question" label
    if echo "$issue_labels" | grep -qiE "wontfix|question|duplicate|invalid"; then
        echo "Issue #${issue_number}: skipping (label: ${issue_labels})."
        continue
    fi

    # Check if a branch already exists for this issue
    branch_name="issue-${issue_number}"
    if echo "$pr_branches" | grep -q "^${branch_name}"; then
        echo "Issue #${issue_number}: PR branch already exists, skipping."
        continue
    fi

    echo "Issue #${issue_number}: ${issue_title}"
    echo "Creating branch and invoking Claude to work on it..."

    # Create a feature branch
    git checkout main && git pull
    git checkout -b "${branch_name}"

    # Build the prompt for Claude
    prompt="You are working on GitHub issue #${issue_number} for the ${REPO} repository.

Issue title: ${issue_title}

Issue body:
${issue_body}

Issue comments:
${issue_comments}

Instructions:
1. Read the codebase to understand the current state of the project.
2. Implement the changes requested in the issue.
3. Write tests for your changes. All tests must pass with 100% coverage: pytest --cov --cov-fail-under=100
4. Commit your changes with descriptive commit messages.
5. Push to the ${branch_name} branch.
6. Create a pull request using: gh pr create --title \"<title>\" --body \"<body>\"
   - Reference the issue in the PR body with \"Closes #${issue_number}\"
7. Never push directly to main."

    # Run Claude in non-interactive mode
    echo "$prompt" | claude --print --dangerously-skip-permissions

    # Return to main
    git checkout main
    echo "Issue #${issue_number}: done."
done
