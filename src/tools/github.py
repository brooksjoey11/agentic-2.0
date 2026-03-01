"""GitHub tool — interact with GitHub repositories via PyGithub."""
import os
from typing import Any

from github import Github


def get_github_client(token: str | None = None) -> Github:
    return Github(token or os.getenv("GITHUB_TOKEN", ""))


def list_repos(org: str, token: str | None = None) -> list[str]:
    gh = get_github_client(token)
    return [repo.full_name for repo in gh.get_organization(org).get_repos()]


def create_issue(repo_full_name: str, title: str, body: str = "", token: str | None = None) -> dict[str, Any]:
    gh = get_github_client(token)
    repo = gh.get_repo(repo_full_name)
    issue = repo.create_issue(title=title, body=body)
    return {"number": issue.number, "url": issue.html_url}


def get_pull_request(repo_full_name: str, pr_number: int, token: str | None = None) -> dict[str, Any]:
    gh = get_github_client(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    return {"number": pr.number, "title": pr.title, "state": pr.state}
