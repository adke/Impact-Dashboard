from flask import Blueprint, jsonify, request
from github import Github, Auth

from config import GITHUB_TOKEN, DEFAULT_DAYS
from cache import get_cached_engineers

bp = Blueprint("api", __name__)


@bp.route("/engineers")
def get_engineers():
    """Return the top N most impactful engineers."""
    days = request.args.get("days", DEFAULT_DAYS, type=int)
    result = get_cached_engineers(days)
    if result is None:
        return jsonify({"status": "loading", "message": "Data is being fetched..."}), 202
    return jsonify(result)


@bp.route("/health")
def health():
    """Health check with GitHub rate limit info."""
    try:
        g = Github(auth=Auth.Token(GITHUB_TOKEN))
        rate_limit = g.get_rate_limit()
        rate = rate_limit.rate
        g.close()
        return jsonify({
            "status": "ok",
            "rate_limit_remaining": rate.remaining,
            "rate_limit_limit": rate.limit,
            "rate_limit_reset": rate.reset.isoformat(),
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500
