#!/usr/bin/env python3
"""Checks open PRs and issues on the repo and takes action.

- Merges approved PRs with passing checks
- Uses Claude Code to address unaddressed PR review comments
- Uses Claude Code to work on open GitHub issues

Intended to be run via cron or CI, outside of a live Claude session.
"""

import json
import os
import shutil
import subprocess
import sys

REPO = "loughmiller/connect-four"
WORK_DIR = os.environ.get("MANAGE_GITHUB_WORK_DIR", "/workspace")

# ---------------------------------------------------------------------------
# Prompt templates (passed to Claude Code via run_claude)
# ---------------------------------------------------------------------------

PR_PROMPT_TEMPLATE = """\
You are working on PR #{pr_number} on the {pr_branch} branch of {repo}.

Here are the reviews (with state and body) on this PR:
{reviews}

Here are the inline review comments on this PR:
{review_comments}

Here are the issue/conversation comments on this PR:
{issue_comments}

For each piece of unaddressed feedback:
- If the feedback requests a change and you agree, implement it, run tests (pytest --cov --cov-fail-under=100), commit, and push to the {pr_branch} branch.
- If the feedback requests a change and you disagree, reply to the comment via the gh API explaining your reasoning and ask for clarification before making changes.
- If the feedback is a question (not a change request), reply to the comment via the gh API with a helpful answer.

After addressing all feedback, run tests one final time to make sure everything passes.
Never push directly to main. Only push to the {pr_branch} branch."""

ISSUE_PROMPT_TEMPLATE = """\
You are working on GitHub issue #{issue_number} for the {repo} repository.

Issue title: {issue_title}

Issue body:
{issue_body}

Issue comments:
{issue_comments}

Instructions:
1. Read the codebase to understand the current state of the project.
2. Implement the changes requested in the issue.
3. Write tests for your changes. All tests must pass with 100% coverage: pytest --cov --cov-fail-under=100
4. Commit your changes with descriptive commit messages.
5. Push to the {branch_name} branch.
6. Create a pull request using: gh pr create --title "<title>" --body "<body>"
   - Reference the issue in the PR body with "Closes #{issue_number}"
7. Never push directly to main."""

# ---------------------------------------------------------------------------


def run(cmd, *, check=True, capture=True, **kwargs):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, text=True, check=check,
        capture_output=capture, **kwargs,
    )
    return result.stdout.strip() if capture else ""


def gh_api(endpoint, *, method="GET", fields=None, jq=None):
    """Call the GitHub API via gh CLI and return parsed JSON or string."""
    url = f"repos/{REPO}/{endpoint}".rstrip("/")
    cmd = f'gh api "{url}"'
    if method != "GET":
        cmd += f" -X {method}"
    if fields:
        for key, value in fields.items():
            cmd += f" -f {key}={value}"
    if jq:
        cmd += f" --jq '{jq}'"
        return run(cmd)
    return json.loads(run(cmd))


def verify_prerequisites():
    """Check that gh and claude CLIs are available and authenticated."""
    try:
        gh_api("", jq=".full_name")
    except subprocess.CalledProcessError:
        print(f"Error: gh CLI cannot access {REPO}. Check GITHUB_TOKEN or run 'gh auth login'.")
        sys.exit(1)

    if not shutil.which("claude"):
        print("Error: claude CLI is not installed.")
        sys.exit(1)


def run_claude(prompt):
    """Run Claude Code in non-interactive mode with the given prompt."""
    subprocess.run(
        ["claude", "--print", "--dangerously-skip-permissions"],
        input=prompt, text=True, check=False,
    )


def handle_prs():
    """Process all open pull requests. Returns set of issue numbers closed by merged PRs."""
    pr_numbers = gh_api("pulls", jq=".[].number").split()
    merged_issue_numbers = set()

    for pr_number in pr_numbers:
        print(f"=== Checking PR #{pr_number} ===")

        pr_json = gh_api(f"pulls/{pr_number}")
        pr_branch = pr_json["head"]["ref"]
        pr_head_sha = pr_json["head"]["sha"]

        # Check reviews
        reviews = gh_api(f"pulls/{pr_number}/reviews")
        approved_count = sum(1 for r in reviews if r["state"] == "APPROVED")

        # Check CI status
        checks_pass = True
        try:
            check_state = gh_api(f"commits/{pr_head_sha}/status", jq=".state")
        except subprocess.CalledProcessError:
            check_state = "unknown"
        if check_state in ("failure", "error"):
            checks_pass = False

        # If approved and checks pass, merge
        if approved_count > 0 and checks_pass:
            print(f"PR #{pr_number} is approved with passing checks. Merging...")
            gh_api(f"pulls/{pr_number}/merge", method="PUT", fields={"merge_method": "squash"})
            run("git checkout main && git pull")
            run(f"git branch -d {pr_branch}", check=False)
            # Track issue numbers closed by this merge (branch convention: issue-N)
            if pr_branch.startswith("issue-"):
                try:
                    merged_issue_numbers.add(int(pr_branch[len("issue-"):]))
                except ValueError:
                    pass
            print(f"PR #{pr_number} merged and local branch cleaned up.")
            continue

        # Gather all feedback
        review_comments = gh_api(f"pulls/{pr_number}/comments")
        issue_comments = gh_api(f"issues/{pr_number}/comments")

        review_body_count = sum(1 for r in reviews if r.get("body", "").strip())
        total = len(review_comments) + len(issue_comments) + review_body_count

        if total == 0:
            print(f"PR #{pr_number}: no comments to address.")
            continue

        print(
            f"PR #{pr_number} has feedback: {review_body_count} review(s) with body, "
            f"{len(review_comments)} inline comment(s), {len(issue_comments)} issue comment(s)."
        )
        print("Checking out branch and invoking Claude to address them...")

        run(f"git fetch origin {pr_branch}")
        run(f"git checkout {pr_branch}")
        run(f"git pull origin {pr_branch}")

        prompt = PR_PROMPT_TEMPLATE.format(
            pr_number=pr_number,
            pr_branch=pr_branch,
            repo=REPO,
            reviews=json.dumps(reviews),
            review_comments=json.dumps(review_comments),
            issue_comments=json.dumps(issue_comments),
        )

        run_claude(prompt)

        run("git checkout main")
        print(f"PR #{pr_number}: done processing comments.")

    return merged_issue_numbers


def handle_issues(merged_issue_numbers=None):
    """Process open issues that don't already have a PR."""
    if merged_issue_numbers is None:
        merged_issue_numbers = set()

    issues_output = gh_api(
        "issues", jq="[.[] | select(.pull_request == null)] | .[].number"
    )
    issue_numbers = issues_output.split() if issues_output else []

    pr_branches = gh_api("pulls", jq=".[].head.ref").split()

    for issue_number in issue_numbers:
        print(f"=== Checking issue #{issue_number} ===")

        # Skip issues that were just closed by a merged PR
        if int(issue_number) in merged_issue_numbers:
            print(f"Issue #{issue_number}: just closed by a merged PR, skipping.")
            continue

        issue_json = gh_api(f"issues/{issue_number}")
        issue_title = issue_json["title"]
        issue_body = issue_json.get("body") or ""
        issue_labels = ",".join(label["name"] for label in issue_json.get("labels", []))
        issue_comments = gh_api(f"issues/{issue_number}/comments")

        # Skip issues with certain labels
        skip_labels = {"wontfix", "question", "duplicate", "invalid"}
        if any(label.lower() in skip_labels for label in issue_labels.split(",")):
            print(f"Issue #{issue_number}: skipping (label: {issue_labels}).")
            continue

        # Check if a branch already exists for this issue (open PRs)
        branch_name = f"issue-{issue_number}"
        if branch_name in pr_branches:
            print(f"Issue #{issue_number}: PR branch already exists, skipping.")
            continue

        # Check if any PR (open, merged, or closed) already references this issue
        linked_prs = run(
            f'gh pr list --repo {REPO} --search "issue #{issue_number}" --state all --json number --jq "length"',
            check=False,
        )
        if linked_prs and linked_prs != "0":
            print(f"Issue #{issue_number}: already has a linked PR, skipping.")
            continue

        print(f"Issue #{issue_number}: {issue_title}")
        print("Creating branch and invoking Claude to work on it...")

        run("git checkout main && git pull")
        run(f"git checkout -b {branch_name}")

        prompt = ISSUE_PROMPT_TEMPLATE.format(
            issue_number=issue_number,
            repo=REPO,
            issue_title=issue_title,
            issue_body=issue_body,
            issue_comments=json.dumps(issue_comments),
            branch_name=branch_name,
        )

        run_claude(prompt)

        run("git checkout main")
        print(f"Issue #{issue_number}: done.")


def main():
    verify_prerequisites()

    os.chdir(WORK_DIR)
    run("git checkout main && git pull")
    run("git remote prune origin", check=False)

    merged_issue_numbers = handle_prs()
    handle_issues(merged_issue_numbers)


if __name__ == "__main__":
    main()
