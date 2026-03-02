export function StatsBreakdown({ engineer }) {
    const { breakdown, reasoning } = engineer;

    return (
        <div className="stats-breakdown">
            {reasoning && (
                <div className="stats-breakdown__reasoning">"{reasoning}"</div>
            )}

            <div className="stats-breakdown__bars">
                {/* Refined Contribution */}
                <div className="stat-bar">
                    <div className="stat-bar__header">
                        <span className="stat-bar__label">Refined</span>
                        <span className="stat-bar__value">
                            {breakdown.refined.weighted.toFixed(1)}
                        </span>
                    </div>
                    <div className="stat-bar__track">
                        <div
                            className="stat-bar__fill stat-bar__fill--refined"
                            style={{ width: `${breakdown.refined.normalized}%` }}
                        ></div>
                    </div>
                    <span className="stat-bar__detail">
                        {breakdown.refined.prs_merged} PRs · +{breakdown.refined.additions} / −{breakdown.refined.deletions}
                    </span>
                </div>

                {/* Collaborative Impact */}
                <div className="stat-bar">
                    <div className="stat-bar__header">
                        <span className="stat-bar__label">Collaborative</span>
                        <span className="stat-bar__value">
                            {breakdown.collaborative.weighted.toFixed(1)}
                        </span>
                    </div>
                    <div className="stat-bar__track">
                        <div
                            className="stat-bar__fill stat-bar__fill--collaborative"
                            style={{ width: `${breakdown.collaborative.normalized}%` }}
                        ></div>
                    </div>
                    <span className="stat-bar__detail">
                        {breakdown.collaborative.review_comments} comments · {breakdown.collaborative.prs_reviewed} PRs reviewed
                    </span>
                </div>

                {/* Knowledge Breadth */}
                <div className="stat-bar">
                    <div className="stat-bar__header">
                        <span className="stat-bar__label">Breadth</span>
                        <span className="stat-bar__value">
                            {breakdown.breadth.weighted.toFixed(1)}
                        </span>
                    </div>
                    <div className="stat-bar__track">
                        <div
                            className="stat-bar__fill stat-bar__fill--breadth"
                            style={{ width: `${breakdown.breadth.normalized}%` }}
                        ></div>
                    </div>
                    <span className="stat-bar__detail">
                        {breakdown.breadth.raw} dirs: {breakdown.breadth.directories.slice(0, 4).join(', ')}
                        {breakdown.breadth.directories.length > 4 && '…'}
                    </span>
                </div>
            </div>
        </div>
    );
}
