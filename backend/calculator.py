import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class ImpactCalculator:
    """
    Computes a weighted Impact Index for GitHub engineers based on:
    - Refined Contribution (50%): PRs merged, weighted by additions vs deletions
    - Collaborative Impact (30%): Review comments on others' PRs
    - Knowledge Breadth (20%): Unique top-level directories touched
    """

    WEIGHTS = {
        "refined": 0.50,
        "collaborative": 0.30,
        "breadth": 0.20,
    }

    def __init__(self, pulls: list[dict], comments: list[dict],
                 api_key: str = "", model: str = "openrouter/free"):
        self.pulls = pulls
        self.comments = comments
        self.api_key = api_key
        self.model = model

    def compute(self, top_n: int = 5, days: int = 90) -> list[dict]:
        """Compute impact scores and return top-N engineer profiles."""
        # 1. Group PRs by author
        author_pulls = defaultdict(list)
        author_avatars = {}
        for pr in self.pulls:
            author = pr["author"]
            author_pulls[author].append(pr)
            author_avatars[author] = pr.get("avatar_url", "")

        # 2. Group comments by author (exclude self-comments)
        pr_authors = {}
        for pr in self.pulls:
            pr_authors[pr["number"]] = pr["author"]

        author_comments = defaultdict(list)
        for comment in self.comments:
            commenter = comment["author"]
            # Extract PR number from URL
            pr_number = self._extract_pr_number(comment.get("pr_url", ""))
            pr_author = pr_authors.get(pr_number)

            # Only count comments on OTHER people's PRs
            if pr_author and commenter != pr_author:
                author_comments[commenter].append(comment)

        # 3. Compute raw scores per author
        all_authors = set(list(author_pulls.keys()) + list(author_comments.keys()))
        raw_scores = {}

        for author in all_authors:
            pulls = author_pulls.get(author, [])
            comments = author_comments.get(author, [])

            # Refined: weight cleanup (deletions) higher
            refined = sum(
                min(p["additions"], p["deletions"]) * 1.5
                + max(p["additions"], p["deletions"]) * 0.5
                for p in pulls
            )

            # Collaborative: count of review comments
            collab = len(comments)

            # Breadth: unique top-level directories
            dirs = set()
            for p in pulls:
                for path in p.get("file_paths", []):
                    top_dir = path.split("/")[0] if "/" in path else "root"
                    dirs.add(top_dir)

            raw_scores[author] = {
                "refined_raw": refined,
                "collab_raw": collab,
                "breadth_raw": len(dirs),
                "directories": sorted(dirs),
                "prs_merged": len(pulls),
                "additions": sum(p["additions"] for p in pulls),
                "deletions": sum(p["deletions"] for p in pulls),
                "review_comments": collab,
                "prs_reviewed": len(set(
                    self._extract_pr_number(c.get("pr_url", ""))
                    for c in comments
                )),
                "avatar_url": author_avatars.get(author, ""),
            }

        if not raw_scores:
            return []

        # 4. Normalize to 0-100
        max_refined = max((s["refined_raw"] for s in raw_scores.values()), default=1) or 1
        max_collab = max((s["collab_raw"] for s in raw_scores.values()), default=1) or 1
        max_breadth = max((s["breadth_raw"] for s in raw_scores.values()), default=1) or 1

        scored = []
        for author, stats in raw_scores.items():
            norm_refined = (stats["refined_raw"] / max_refined) * 100
            norm_collab = (stats["collab_raw"] / max_collab) * 100
            norm_breadth = (stats["breadth_raw"] / max_breadth) * 100

            impact = (
                norm_refined * self.WEIGHTS["refined"]
                + norm_collab * self.WEIGHTS["collaborative"]
                + norm_breadth * self.WEIGHTS["breadth"]
            )

            # Determine dominant dimension
            dims = {
                "Refined Contribution": norm_refined,
                "Collaborative Impact": norm_collab,
                "Knowledge Breadth": norm_breadth,
            }
            dominant = max(dims, key=dims.get)

            scored.append({
                "username": author,
                "avatar_url": stats["avatar_url"],
                "impact_score": round(impact, 1),
                "dominant_dimension": dominant,
                "breakdown": {
                    "refined": {
                        "raw": round(stats["refined_raw"], 1),
                        "normalized": round(norm_refined, 1),
                        "weighted": round(norm_refined * self.WEIGHTS["refined"], 1),
                        "prs_merged": stats["prs_merged"],
                        "additions": stats["additions"],
                        "deletions": stats["deletions"],
                    },
                    "collaborative": {
                        "raw": stats["collab_raw"],
                        "normalized": round(norm_collab, 1),
                        "weighted": round(norm_collab * self.WEIGHTS["collaborative"], 1),
                        "review_comments": stats["review_comments"],
                        "prs_reviewed": stats["prs_reviewed"],
                    },
                    "breadth": {
                        "raw": stats["breadth_raw"],
                        "normalized": round(norm_breadth, 1),
                        "weighted": round(norm_breadth * self.WEIGHTS["breadth"], 1),
                        "directories": stats["directories"],
                    },
                },
            })

        # 5. Sort and take top N
        scored.sort(key=lambda x: x["impact_score"], reverse=True)
        top = scored[:top_n]

        # 6. Generate LLM tags for top N (parallel — all calls run concurrently)
        with ThreadPoolExecutor(max_workers=top_n) as executor:
            futures = {
                executor.submit(self._generate_tag, eng, days): i
                for i, eng in enumerate(top)
            }
            for future in as_completed(futures):
                i = futures[future]
                tag_data = future.result()
                top[i]["tag"] = tag_data.get("tag", "Contributor")
                top[i]["reasoning"] = tag_data.get("reasoning", "")
                top[i]["rank"] = i + 1

        return top

    def _generate_tag(self, engineer: dict, days: int) -> dict:
        """Generate a tag and reasoning using OpenRouter, with rule-based fallback."""
        stats = {
            "prs_merged": engineer["breakdown"]["refined"]["prs_merged"],
            "additions": engineer["breakdown"]["refined"]["additions"],
            "deletions": engineer["breakdown"]["refined"]["deletions"],
            "review_comments": engineer["breakdown"]["collaborative"]["review_comments"],
            "prs_reviewed": engineer["breakdown"]["collaborative"]["prs_reviewed"],
            "directories": engineer["breakdown"]["breadth"]["directories"],
            "dominant_dimension": engineer["dominant_dimension"],
        }

        if not self.api_key:
            return self._fallback_tag(stats)

        try:
            prompt = self._build_prompt(stats, days)
            resp = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            # The model may wrap JSON in markdown fences — strip them
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

            result = json.loads(content)

            if "tag" in result and "reasoning" in result:
                return result
            return self._fallback_tag(stats)

        except Exception:
            return self._fallback_tag(stats)

    @staticmethod
    def _build_prompt(stats: dict, days: int) -> str:
        top_dirs = ", ".join(stats["directories"][:8]) if stats["directories"] else "N/A"
        return f"""You are an engineering analytics assistant. Given the following contribution
stats for a GitHub engineer over the last {days} days on the PostHog/posthog
repository, generate:
1. A creative 2-3 word "tag" (e.g. "The Architect", "Infra Guardian")
2. A single-sentence "reasoning" string that explains WHY this person is
   impactful, citing specific numbers from the data.

Stats:
- PRs merged: {stats['prs_merged']}
- Total additions: {stats['additions']}
- Total deletions: {stats['deletions']}
- Review comments on others' PRs: {stats['review_comments']}
- Unique PRs reviewed: {stats['prs_reviewed']}
- Unique directories touched: {len(stats['directories'])}
- Top directories: {top_dirs}
- Dominant dimension: {stats['dominant_dimension']}

Respond ONLY with valid JSON: {{"tag": "...", "reasoning": "..."}}"""

    @staticmethod
    def _fallback_tag(stats: dict) -> dict:
        """Rule-based fallback when the LLM is unavailable."""
        dominant = stats.get("dominant_dimension", "")

        if "Refined" in dominant:
            tag = "The Builder"
            reasoning = (
                f"Merged {stats['prs_merged']} PRs with "
                f"{stats['additions']} additions and {stats['deletions']} deletions."
            )
        elif "Collaborative" in dominant:
            tag = "The Reviewer"
            reasoning = (
                f"{stats['review_comments']} review comments across "
                f"{stats['prs_reviewed']} PRs — strong mentorship signal."
            )
        elif "Breadth" in dominant:
            tag = "The Polymath"
            dirs = ", ".join(stats["directories"][:5])
            reasoning = (
                f"Touched {len(stats['directories'])} unique directories "
                f"including {dirs}."
            )
        else:
            tag = "Contributor"
            reasoning = f"Merged {stats['prs_merged']} PRs in the last period."

        return {"tag": tag, "reasoning": reasoning}

    @staticmethod
    def _extract_pr_number(pr_url: str) -> int | None:
        """Extract PR number from a GitHub API URL."""
        if not pr_url:
            return None
        match = re.search(r"/pulls/(\d+)", pr_url)
        return int(match.group(1)) if match else None
