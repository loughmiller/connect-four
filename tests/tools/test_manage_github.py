import json
import subprocess
from unittest.mock import patch, mock_open, call

import tools.manage_github as manage_github


# --- run() ---

@patch("tools.manage_github.subprocess.run")
def test_run_returns_stripped_stdout(mock_subproc):
    """run() captures stdout and strips whitespace."""
    mock_subproc.return_value.stdout = "  hello  "
    result = manage_github.run("echo hello")
    assert result == "hello"
    mock_subproc.assert_called_once_with(
        "echo hello", shell=True, text=True, check=True, capture_output=True,
    )


@patch("tools.manage_github.subprocess.run")
def test_run_capture_false_returns_empty(mock_subproc):
    """run() with capture=False returns empty string."""
    result = manage_github.run("echo hello", capture=False)
    assert result == ""
    mock_subproc.assert_called_once_with(
        "echo hello", shell=True, text=True, check=True, capture_output=False,
    )


# --- gh_api() ---

@patch("tools.manage_github.run")
def test_gh_api_get_with_jq(mock_run):
    """gh_api() with jq passes raw string through."""
    mock_run.return_value = "loughmiller/connect-four"
    result = manage_github.gh_api("", jq=".full_name")
    mock_run.assert_called_once_with(
        'gh api "repos/loughmiller/connect-four" --jq \'.full_name\''
    )
    assert result == "loughmiller/connect-four"


@patch("tools.manage_github.run")
def test_gh_api_get_returns_parsed_json(mock_run):
    """gh_api() without jq parses JSON response."""
    mock_run.return_value = '{"id": 1}'
    result = manage_github.gh_api("pulls/1")
    mock_run.assert_called_once_with(
        'gh api "repos/loughmiller/connect-four/pulls/1"'
    )
    assert result == {"id": 1}


@patch("tools.manage_github.run")
def test_gh_api_with_method_and_fields(mock_run):
    """gh_api() includes -X and -f flags for method/fields."""
    mock_run.return_value = "{}"
    manage_github.gh_api("pulls/1/merge", method="PUT", fields={"merge_method": "squash"})
    cmd = mock_run.call_args[0][0]
    assert "-X PUT" in cmd
    assert "-f merge_method=squash" in cmd


@patch("tools.manage_github.run")
def test_gh_api_strips_trailing_slash(mock_run):
    """gh_api() with empty endpoint doesn't leave a trailing slash."""
    mock_run.return_value = '"loughmiller/connect-four"'
    manage_github.gh_api("", jq=".full_name")
    cmd = mock_run.call_args[0][0]
    assert '"repos/loughmiller/connect-four"' in cmd
    assert 'connect-four/"' not in cmd


# --- load_secrets() ---

@patch("tools.manage_github.os.path.isfile", side_effect=lambda f: f == manage_github.ENV_FILE)
@patch("builtins.open", mock_open(read_data="GH_TOKEN=abc123\n# comment\n\nANTHROPIC_API_KEY=sk-test\n"))
@patch.dict("os.environ", {}, clear=True)
def test_load_secrets_from_env_file(mock_isfile):
    """load_secrets() reads .env file and sets env vars."""
    manage_github.load_secrets()
    import os
    assert os.environ["GH_TOKEN"] == "abc123"
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test"


@patch("tools.manage_github.os.path.isfile", return_value=False)
def test_load_secrets_no_file(mock_isfile):
    """load_secrets() is a no-op when no secrets file exists."""
    manage_github.load_secrets()


# --- verify_prerequisites() ---

@patch("tools.manage_github.shutil.which", return_value="/usr/bin/claude")
@patch("tools.manage_github.gh_api", return_value="loughmiller/connect-four")
def test_verify_prerequisites_success(mock_gh, mock_which):
    """verify_prerequisites() passes when gh and claude are available."""
    manage_github.verify_prerequisites()


@patch("tools.manage_github.sys.exit")
@patch("tools.manage_github.gh_api", side_effect=subprocess.CalledProcessError(1, "gh"))
def test_verify_prerequisites_gh_fails(mock_gh, mock_exit):
    """verify_prerequisites() exits when gh API call fails."""
    manage_github.verify_prerequisites()
    mock_exit.assert_called_once_with(1)


@patch("tools.manage_github.sys.exit")
@patch("tools.manage_github.shutil.which", return_value=None)
@patch("tools.manage_github.gh_api", return_value="loughmiller/connect-four")
def test_verify_prerequisites_no_claude(mock_gh, mock_which, mock_exit):
    """verify_prerequisites() exits when claude CLI is missing."""
    manage_github.verify_prerequisites()
    mock_exit.assert_called_once_with(1)


# --- run_claude() ---

@patch("tools.manage_github.subprocess.run")
def test_run_claude_calls_subprocess(mock_subproc):
    """run_claude() invokes claude CLI with --print flag."""
    manage_github.run_claude("fix the bug")
    mock_subproc.assert_called_once_with(
        ["claude", "--print", "--dangerously-skip-permissions"],
        input="fix the bug", text=True, check=False,
    )


# --- handle_prs() ---

@patch("tools.manage_github.gh_api")
def test_handle_prs_no_prs(mock_gh):
    """handle_prs() does nothing when no open PRs exist."""
    mock_gh.return_value = ""
    result = manage_github.handle_prs()
    mock_gh.assert_called_once()
    assert result == set()


@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_prs_approved_passing_merges(mock_gh, mock_run):
    """Approved PR with passing checks gets squash-merged and branch cleaned up."""
    mock_gh.side_effect = [
        "42",                                                   # pulls jq -> pr numbers
        {"head": {"ref": "feat-x", "sha": "abc123"}},          # pulls/42
        [{"state": "APPROVED", "body": ""}],                    # pulls/42/reviews
        "success",                                              # commits/abc123/status
        {},                                                     # pulls/42/merge
    ]
    result = manage_github.handle_prs()
    # Verify merge was called
    merge_call = mock_gh.call_args_list[4]
    assert "merge" in merge_call[0][0]
    assert merge_call[1]["method"] == "PUT"
    # Verify git cleanup
    mock_run.assert_any_call("git checkout main && git pull")
    mock_run.assert_any_call("git branch -d feat-x", check=False)
    # Non-issue branch: no issue numbers tracked
    assert result == set()


@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_prs_merge_issue_branch_tracks_number(mock_gh, mock_run):
    """Merging a PR from an issue-N branch returns the issue number."""
    mock_gh.side_effect = [
        "10",                                                   # pulls jq -> pr numbers
        {"head": {"ref": "issue-7", "sha": "def456"}},         # pulls/10
        [{"state": "APPROVED", "body": ""}],                    # reviews
        "success",                                              # status
        {},                                                     # merge
    ]
    result = manage_github.handle_prs()
    assert result == {7}


@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_prs_merge_issue_branch_non_numeric_ignored(mock_gh, mock_run):
    """Merging a PR from issue-abc branch doesn't crash."""
    mock_gh.side_effect = [
        "10",
        {"head": {"ref": "issue-abc", "sha": "def456"}},
        [{"state": "APPROVED", "body": ""}],
        "success",
        {},
    ]
    result = manage_github.handle_prs()
    assert result == set()


@patch("tools.manage_github.run_claude")
@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_prs_approved_failing_checks_processes_feedback(mock_gh, mock_run, mock_claude):
    """Approved PR with failing checks still processes review feedback via Claude."""
    mock_gh.side_effect = [
        "42",                                                   # pulls jq
        {"head": {"ref": "feat-x", "sha": "abc123"}},          # pulls/42
        [{"state": "APPROVED", "body": "looks good"}],          # reviews
        "failure",                                              # status -> checks fail
        [{"body": "fix typo"}],                                 # review comments
        [{"body": "nice work"}],                                # issue comments
    ]
    manage_github.handle_prs()
    mock_claude.assert_called_once()


@patch("tools.manage_github.run_claude")
@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_prs_no_comments_skips(mock_gh, mock_run, mock_claude):
    """PR with no actionable comments skips Claude invocation."""
    mock_gh.side_effect = [
        "42",                                                   # pulls jq
        {"head": {"ref": "feat-x", "sha": "abc123"}},          # pulls/42
        [{"state": "CHANGES_REQUESTED", "body": ""}],           # reviews (no body)
        "success",                                              # status
        [],                                                     # review comments (empty)
        [],                                                     # issue comments (empty)
    ]
    manage_github.handle_prs()
    mock_claude.assert_not_called()


@patch("tools.manage_github.run_claude")
@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_prs_with_feedback_invokes_claude(mock_gh, mock_run, mock_claude):
    """PR with review comments invokes Claude on the feature branch."""
    mock_gh.side_effect = [
        "42",                                                   # pulls jq
        {"head": {"ref": "feat-x", "sha": "abc123"}},          # pulls/42
        [{"state": "CHANGES_REQUESTED", "body": ""}],           # reviews
        "success",                                              # status
        [{"body": "fix this"}],                                 # review comments
        [],                                                     # issue comments
    ]
    manage_github.handle_prs()
    mock_claude.assert_called_once()
    prompt = mock_claude.call_args[0][0]
    assert "PR #42" in prompt
    assert "feat-x" in prompt
    mock_run.assert_any_call("git fetch origin feat-x")
    mock_run.assert_any_call("git checkout feat-x")
    mock_run.assert_any_call("git pull origin feat-x")
    mock_run.assert_any_call("git checkout main")


@patch("tools.manage_github.run_claude")
@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_prs_check_status_error_treated_as_unknown(mock_gh, mock_run, mock_claude):
    """Status API error is treated as non-failure, allowing merge if approved."""
    mock_gh.side_effect = [
        "42",                                                   # pulls jq
        {"head": {"ref": "feat-x", "sha": "abc123"}},          # pulls/42
        [{"state": "APPROVED", "body": ""}],                    # reviews (approved)
        subprocess.CalledProcessError(1, "gh"),                 # status -> error
        # approved + checks_pass (unknown != failure) -> merge
        {},                                                     # pulls/42/merge
    ]
    manage_github.handle_prs()
    merge_call = mock_gh.call_args_list[4]
    assert "merge" in merge_call[0][0]


# --- handle_issues() ---

@patch("tools.manage_github.gh_api")
def test_handle_issues_no_issues(mock_gh):
    """handle_issues() does nothing when no open issues exist."""
    mock_gh.side_effect = [
        "",     # issues jq -> empty
        "",     # pulls jq -> branches
    ]
    manage_github.handle_issues()


@patch("tools.manage_github.run_claude")
@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_issues_skips_recently_merged(mock_gh, mock_run, mock_claude):
    """Issues whose PR was just merged are skipped."""
    mock_gh.side_effect = [
        "5",    # issues jq
        "",     # pulls jq (no branches)
    ]
    manage_github.handle_issues(merged_issue_numbers={5})
    mock_claude.assert_not_called()


@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_issues_skip_label(mock_gh, mock_run):
    """Issues with skip labels (wontfix, etc.) are not processed."""
    mock_gh.side_effect = [
        "5",                                                    # issues jq
        "",                                                     # pulls jq (no branches)
        {"title": "Bug", "body": "fix it",
         "labels": [{"name": "wontfix"}]},                     # issues/5
        [],                                                     # issues/5/comments
    ]
    manage_github.handle_issues()
    # Should not create a branch
    assert not any("checkout -b" in str(c) for c in mock_run.call_args_list)


@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_issues_existing_branch_skips(mock_gh, mock_run):
    """Issues with an existing PR branch are skipped."""
    mock_gh.side_effect = [
        "5",                                                    # issues jq
        "issue-5",                                              # pulls jq -> branch exists
        {"title": "Bug", "body": "fix it", "labels": []},      # issues/5
        [],                                                     # issues/5/comments
    ]
    manage_github.handle_issues()
    assert not any("checkout -b" in str(c) for c in mock_run.call_args_list)


@patch("tools.manage_github.run_claude")
@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_issues_linked_pr_skips(mock_gh, mock_run, mock_claude):
    """Issues that already have a linked PR are skipped."""
    mock_gh.side_effect = [
        "5",                                                    # issues jq
        "",                                                     # pulls jq (no branches)
        {"title": "Bug", "body": "fix it", "labels": []},      # issues/5
        [],                                                     # issues/5/comments
    ]
    # The linked PR check uses run(), not gh_api
    mock_run.return_value = "1"
    manage_github.handle_issues()
    mock_claude.assert_not_called()


@patch("tools.manage_github.run_claude")
@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_issues_normal_processing(mock_gh, mock_run, mock_claude):
    """Normal issue creates a branch and invokes Claude with issue details."""
    mock_gh.side_effect = [
        "5",                                                    # issues jq
        "",                                                     # pulls jq (no branches)
        {"title": "Add feature", "body": "please", "labels": []},  # issues/5
        [{"body": "me too"}],                                   # issues/5/comments
    ]
    mock_run.return_value = "0"  # no linked PRs
    manage_github.handle_issues()
    mock_claude.assert_called_once()
    prompt = mock_claude.call_args[0][0]
    assert "issue #5" in prompt
    assert "Add feature" in prompt
    assert "please" in prompt


@patch("tools.manage_github.run_claude")
@patch("tools.manage_github.run")
@patch("tools.manage_github.gh_api")
def test_handle_issues_none_body_defaults_to_empty(mock_gh, mock_run, mock_claude):
    """Issue with None body defaults to empty string in prompt."""
    mock_gh.side_effect = [
        "5",
        "",
        {"title": "Bug", "body": None, "labels": []},
        [],
    ]
    mock_run.return_value = "0"
    manage_github.handle_issues()
    prompt = mock_claude.call_args[0][0]
    assert "Issue body:\n\n" in prompt


# --- main() ---

@patch("tools.manage_github.handle_issues")
@patch("tools.manage_github.handle_prs")
@patch("tools.manage_github.run")
@patch("tools.manage_github.os.chdir")
@patch("tools.manage_github.verify_prerequisites")
@patch("tools.manage_github.load_secrets")
def test_main_orchestrates_correctly(mock_secrets, mock_verify, mock_chdir, mock_run, mock_prs, mock_issues):
    """main() passes merged issue numbers from handle_prs to handle_issues."""
    mock_prs.return_value = {7, 12}
    manage_github.main()
    mock_secrets.assert_called_once()
    mock_verify.assert_called_once()
    mock_chdir.assert_called_once_with(manage_github.WORK_DIR)
    mock_run.assert_any_call("git checkout main && git pull")
    mock_run.assert_any_call("git remote prune origin", check=False)
    mock_prs.assert_called_once()
    mock_issues.assert_called_once_with({7, 12})
