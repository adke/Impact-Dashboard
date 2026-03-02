import requests
import time
from datetime import datetime, timedelta, timezone

GRAPHQL_URL = "https://api.github.com/graphql"

# Combined GraphQL query: fetches merged PRs with additions, deletions,
# file paths, AND review comments all in ONE paginated pass.
COMBINED_QUERY = """
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(
      states: MERGED,
      first: 100,
      after: $cursor,
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        number
        title
        mergedAt
        additions
        deletions
        author {
          login
          avatarUrl
        }
        files(first: 50) {
          nodes {
            path
          }
        }
        reviews(first: 50) {
          nodes {
            author {
              login
            }
            comments(first: 20) {
              totalCount
            }
          }
        }
      }
    }
  }
}
"""


def _graphql(token: str, query: str, variables: dict) -> dict:
    """Execute a GraphQL query against GitHub's API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    return data["data"]


def get_pr_data(token: str, repo_name: str, days: int = 90) -> tuple[list[dict], list[dict]]:
    """
    Fetch merged PRs AND review comments in a single paginated GraphQL pass.
    Returns (pulls, comments) — same format as the old separate functions.
    """
    owner, repo = repo_name.split("/")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pulls_data = []
    comments_data = []
    cursor = None
    done = False

    page_num = 0
    total_start = time.time()

    while not done:
        page_num += 1
        page_start = time.time()
        data = _graphql(token, COMBINED_QUERY, {
            "owner": owner,
            "repo": repo,
            "cursor": cursor,
        })
        page_elapsed = time.time() - page_start

        pr_nodes = data["repository"]["pullRequests"]["nodes"]
        page_info = data["repository"]["pullRequests"]["pageInfo"]
        print(f"[GitHub] Page {page_num}: fetched {len(pr_nodes)} PRs in {page_elapsed:.1f}s (total PRs so far: {len(pulls_data) + len(pr_nodes)})")

        for pr in pr_nodes:
            merged_at = datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00"))
            if merged_at < cutoff:
                done = True
                break

            # Skip bot accounts
            if not pr.get("author"):
                continue

            author_login = pr["author"]["login"]

            # -- Extract PR data --
            file_paths = [f["path"] for f in (pr.get("files", {}).get("nodes", []) or [])]

            pulls_data.append({
                "number": pr["number"],
                "title": pr["title"],
                "author": author_login,
                "avatar_url": pr["author"]["avatarUrl"],
                "merged_at": pr["mergedAt"],
                "additions": pr["additions"],
                "deletions": pr["deletions"],
                "file_paths": file_paths,
            })

            # -- Extract review comments --
            for review in (pr.get("reviews", {}).get("nodes", []) or []):
                reviewer = review.get("author", {})
                if not reviewer:
                    continue
                reviewer_login = reviewer.get("login", "")

                comment_count = review.get("comments", {}).get("totalCount", 0)
                if comment_count > 0 and reviewer_login != author_login:
                    comments_data.append({
                        "author": reviewer_login,
                        "pr_url": f"https://api.github.com/repos/{repo_name}/pulls/{pr['number']}",
                        "body_length": 100,  # approximate
                        "created_at": pr["mergedAt"],
                    })

        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    total_elapsed = time.time() - total_start
    print(f"[GitHub] DONE: {page_num} pages, {len(pulls_data)} PRs, {len(comments_data)} comments in {total_elapsed:.1f}s")
    return pulls_data, comments_data
