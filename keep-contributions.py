"""keep-contributions.py

Scans your org and provides you with the info you need to keep your
contributions...

Author: Andreas Poehlmann
Email: andreas@poehlmann.io

"""
from __future__ import annotations

import os
import pathlib
from typing import Iterator
from typing import NamedTuple

import requests


class Context:
    def __init__(
        self,
        token: str,
        request_kwargs: dict | None = None,
        last_cursor: str = "null",
        checked: int = 0,
    ) -> None:
        self.token = token
        self.request_kwargs = request_kwargs
        self.last_cursor = last_cursor
        self.checked = checked


class ContributionInfo(NamedTuple):
    name: str
    is_private: bool
    user: str
    has_commits: bool
    is_starred: bool
    is_issue_author: bool
    is_pr_author: bool


def retrieve_repository_contribution_info(
    ctx: Context,
    owner: str,
    repository: str,
    user: str
) -> ContributionInfo:
    """retrieves the contribution information for a specific repository"""
    q = """\
    {
      repository(name: "%(name)s", owner: "%(owner)s") {
        %(is_private)s
        %(has_commits)s
        %(stargazers)s
        %(issues)s
        %(pull_requests)s
      }
    }
    """
    q_is_private = "isPrivate"
    q_has_commits = """
        defaultBranchRef {
          name
          target {
            ... on Commit {
              id
              history(first: 100, after: %s) {
                edges {
                  node {
                    committer {
                      user {
                        login
                      }
                    }
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
          }
        }
    """
    q_stargazers = """
        stargazers(first: 100, after: %s) {
          nodes {
            login
            email
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
    """
    q_issues = """
        issues(first: 100, after: %s) {
          nodes {
            author {
              login
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
    """
    q_prs = """
        pullRequests(first: 100, after: %s) {
          nodes {
            author {
              login
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
    """

    is_private = has_commits = is_starred = is_issue_author = is_pr_author = None
    cursor_commits = cursor_stargazers = cursor_issues = cursor_prs = "null"

    while (
        is_private is None
        or has_commits is None
        or is_starred is None
        or is_issue_author is None
        or is_pr_author is None
    ):
        x = q % dict(
            owner=owner,
            name=repository,
            # disable parts of the query if we don't need them anymore
            has_commits=q_has_commits % cursor_commits if has_commits is None else "",
            is_private=q_is_private if is_private is None else "",
            stargazers=q_stargazers % cursor_stargazers if is_starred is None else "",
            issues=q_issues % cursor_issues if is_issue_author is None else "",
            pull_requests=q_prs % cursor_prs if is_pr_author is None else "",
        )
        request = requests.post(
            "https://api.github.com/graphql",
            json={"query": x},
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {ctx.token}",
            },
            **(ctx.request_kwargs or {}),
        )
        if request.status_code != 200:
            raise RuntimeError(
                f"status: {request.status_code}\n"
                f"content: {request.content!r}"
            )
        data = request.json()
        repo = data['data']['repository']

        if is_private is None:
            is_private = repo["isPrivate"]
        if has_commits is None:
            default_branch_reference = repo["defaultBranchRef"]
            if default_branch_reference is None:
                commit_history = {"edges": [], "pageInfo": {"hasNextPage": False}}
            else:
                commit_history = repo["defaultBranchRef"]["target"]["history"]
            for edge in commit_history["edges"]:
                committer_user = edge["node"]["committer"]["user"]
                if committer_user is None:
                    continue
                if committer_user["login"] == user:
                    has_commits = True
                    break
            else:
                page_info = commit_history["pageInfo"]
                if page_info["hasNextPage"]:
                    cursor_commits = '"{}"'.format(page_info['endCursor'])
                else:
                    has_commits = False
        if is_starred is None:
            for user_info in repo["stargazers"]["nodes"]:
                if user_info["login"] == user:
                    is_starred = True
                    break
            else:
                page_info = repo["stargazers"]["pageInfo"]
                if page_info["hasNextPage"]:
                    cursor_stargazers = '"{}"'.format(page_info['endCursor'])
                else:
                    is_starred = False
        if is_issue_author is None:
            for user_info in repo["issues"]["nodes"]:
                author = user_info["author"]
                if author is None:
                    continue
                elif author["login"] == user:
                    is_issue_author = True
                    break
            else:
                page_info = repo["issues"]["pageInfo"]
                if page_info["hasNextPage"]:
                    cursor_issues = '"{}"'.format(page_info['endCursor'])
                else:
                    is_issue_author = False
        if is_pr_author is None:
            for user_info in repo["pullRequests"]["nodes"]:
                author = user_info["author"]
                if author is None:
                    continue
                elif author["login"] == user:
                    is_pr_author = True
                    break
            else:
                page_info = repo["pullRequests"]["pageInfo"]
                if page_info["hasNextPage"]:
                    cursor_prs = '"{}"'.format(page_info['endCursor'])
                else:
                    is_pr_author = False
    return ContributionInfo(
        f"{owner}/{repository}",
        is_private,
        user,
        has_commits,
        is_starred,
        is_issue_author,
        is_pr_author,
    )


def query_all_contributed_repos(ctx: Context, *, org: str, user: str) -> Iterator[ContributionInfo]:
    template_query = """\
    {
      organization(login: "%s") {
        repositories(first: 20, after: %s) {
          nodes {
            name
            defaultBranchRef {
              name
              target {
                ... on Commit {
                  id
                  history(first: 100, after: null) {
                    edges {
                      node {
                        committer {
                          user {
                            login
                          }
                          email
                        }
                      }
                    }
                    pageInfo {
                      hasNextPage
                      endCursor
                    }
                    totalCount
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
          totalCount
        }
      }
      rateLimit {
        limit
        cost
        remaining
        resetAt
      }
    }
    """
    while True:
        request = requests.post(
            "https://api.github.com/graphql",
            json={"query": template_query % (org, ctx.last_cursor)},
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {ctx.token}",
            },
            **(ctx.request_kwargs or {}),
        )
        if request.status_code != 200:
            raise RuntimeError(
                f"status: {request.status_code}\n"
                f"content: {request.content!r}"
            )
        data = request.json()
        repos = data['data']['organization']['repositories']

        for repo in repos['nodes']:
            default_branch_reference = repo["defaultBranchRef"]
            if default_branch_reference is None:
                print("# skipping empty:", repo)
                continue

            commit_history = repo["defaultBranchRef"]["target"]["history"]
            for edge in commit_history["edges"]:
                committer_user = edge["node"]["committer"]["user"]
                if committer_user is None:
                    continue
                if committer_user["login"] == user:
                    contributed = True
                    break
            else:
                contributed = False

            if (
                not contributed
                and not commit_history["pageInfo"]["hasNextPage"]
            ):
                pass  # no commits in here
            else:
                info = retrieve_repository_contribution_info(ctx, owner=org, repository=repo["name"], user=user)
                if (
                    not info.has_commits
                    and not info.is_pr_author
                    and not info.is_issue_author
                ):
                    pass
                else:
                    yield info

        # check next page
        page_info = repos['pageInfo']
        if not page_info["hasNextPage"]:
            break
        else:
            ctx.checked += len(repos["nodes"])
            ctx.last_cursor = f'''"{page_info['endCursor']}"'''
            rate_limit = data['data']['rateLimit']
            print(f"# {ctx.checked} of {repos['totalCount']} with {rate_limit['remaining']} of {rate_limit['limit']} reset at {rate_limit['resetAt']} -> next cursor {ctx.last_cursor}")


if __name__ == "__main__":
    import shelve
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default=None)
    parser.add_argument("--token-file", default=None)
    parser.add_argument("org", help="the github org you want to scan")
    parser.add_argument("user", help="your github user name")
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--rescan-contributed", action="store_true")
    args = parser.parse_args()

    if not args.scan and not args.rescan_contributed:
        with shelve.open(f".cache-{args.org}", flag="r") as db:
            print(
                    "# STATUS private commits stars issue prs repository"
            )
            for _, r in sorted(db["repositories"].items()):
                x = {True: ". ", False: "!!"}
                if not r.is_private:
                    contributions_ok = r.is_starred
                else:
                    contributions_ok = r.is_starred and (r.is_issue_author or r.is_pr_author)
                print(
                    " %s    %s      %s      %s    %s    %s  %s" % (
                        "    " if contributions_ok else "WARN",
                        x[not r.is_private],
                        x[r.has_commits],
                        x[r.is_starred],
                        x[r.is_issue_author],
                        x[r.is_pr_author],
                        r.name
                    )
                )
        raise SystemExit(0)

    elif args.scan and args.rescan_contributed:
        print("pick --scan OR --rescan-contributed")
        raise SystemExit(1)

    else:
        assert args.scan ^ args.rescan_contributed

        if args.token is None:
            if args.token_file is None:
                GH_TOKEN = os.environ["GH_TOKEN"]  # needs to be a classic PAT Token
            else:
                GH_TOKEN = pathlib.Path(args.token_file).read_text().strip()
        else:
            GH_TOKEN = args.token

        ctx = Context(token=GH_TOKEN, request_kwargs={}, last_cursor="null")

        with shelve.open(f".cache-{args.org}") as db:
            try:
                ctx.last_cursor = db["last_cursor"]
                ctx.checked = db["checked"]
            except KeyError:
                ctx.last_cursor = "null"
                ctx.checked = 0

            try:
                repos = db["repositories"]
            except KeyError:
                repos = {}
            try:
                if args.rescan_contributed:
                    for r_name in repos:
                        _, name = r_name.split("/", maxsplit=1)
                        r = retrieve_repository_contribution_info(ctx, owner=args.org, repository=name, user=args.user)
                        print(r)
                        assert r_name == r.name
                        repos[r.name] = r
                elif args.scan:
                    for r in query_all_contributed_repos(ctx, org=args.org, user=args.user):
                        print(r)
                        repos[r.name] = r
            finally:
                db["repositories"] = repos
                db["last_cursor"] = ctx.last_cursor
                db["checked"] = ctx.checked

