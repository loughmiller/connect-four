#!/usr/bin/env bash
# Checks open PRs on loughmiller/connect-four and takes action:
# - Merges approved PRs with passing checks
# - Uses Claude Code to address unaddressed review comments
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

# Get open PRs (JSON array)
prs=$(gh api "repos/${REPO}/pulls" --jq '.[].number')

if [ -z "$prs" ]; then
    exit 0
fi

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
- If you agree with the requested change, implement it, run tests (pytest --cov --cov-fail-under=100), commit, and push to the ${pr_branch} branch.
- If you disagree, reply to the comment via the gh API explaining your reasoning and ask for clarification before making changes.

After addressing all feedback, run tests one final time to make sure everything passes.
Never push directly to main. Only push to the ${pr_branch} branch."

    # Run Claude in non-interactive mode to address the comments
    echo "$prompt" | claude --print --dangerously-skip-permissions

    # Return to main
    git checkout main
    echo "PR #${pr_number}: done processing comments."
done
