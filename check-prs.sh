#!/usr/bin/env bash
# Checks open PRs on loughmiller/connect-four and takes action:
# - Merges approved PRs with passing checks
# - Addresses unaddressed review comments
#
# Intended to be run via cron or CI, outside of a live Claude session.

set -euo pipefail

REPO="loughmiller/connect-four"

# Load secrets if available
if [ -f /workspace/.devcontainer/load-secrets.sh ]; then
    bash /workspace/.devcontainer/load-secrets.sh
    # shellcheck disable=SC1090
    source ~/.zshenv 2>/dev/null || true
fi

# Verify gh is authenticated
if ! gh auth status &>/dev/null; then
    echo "Error: gh CLI is not authenticated. Set GITHUB_TOKEN or run 'gh auth login'."
    exit 1
fi

cd /workspace

# Get open PRs (JSON array)
prs=$(gh api "repos/${REPO}/pulls" --jq '.[].number')

if [ -z "$prs" ]; then
    exit 0
fi

for pr_number in $prs; do
    echo "=== Checking PR #${pr_number} ==="

    # Get PR details
    pr_branch=$(gh api "repos/${REPO}/pulls/${pr_number}" --jq '.head.ref')

    # Check reviews
    approved=$(gh api "repos/${REPO}/pulls/${pr_number}/reviews" --jq '[.[] | select(.state == "APPROVED")] | length')

    # Check CI status
    checks_pass=true
    check_state=$(gh api "repos/${REPO}/commits/$(gh api "repos/${REPO}/pulls/${pr_number}" --jq '.head.sha')/status" --jq '.state' 2>/dev/null || echo "unknown")
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

    # Check for unaddressed review comments
    comments=$(gh api "repos/${REPO}/pulls/${pr_number}/comments")
    comment_count=$(echo "$comments" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")

    if [ "$comment_count" -gt 0 ]; then
        echo "PR #${pr_number} has ${comment_count} review comment(s) — manual review needed."
        echo "  Branch: ${pr_branch}"
        echo "  Run: gh api repos/${REPO}/pulls/${pr_number}/comments | python3 -m json.tool"
    fi

    # Check issue comments too
    issue_comments=$(gh api "repos/${REPO}/issues/${pr_number}/comments")
    issue_comment_count=$(echo "$issue_comments" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")

    if [ "$issue_comment_count" -gt 0 ]; then
        echo "PR #${pr_number} has ${issue_comment_count} issue comment(s) — check for requests."
    fi
done
