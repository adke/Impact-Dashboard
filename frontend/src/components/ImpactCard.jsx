import { useState } from 'react';
import { StatsBreakdown } from './StatsBreakdown';

export function ImpactCard({ engineer }) {
    const [expanded, setExpanded] = useState(false);
    const { rank, username, avatar_url, impact_score, tag } = engineer;

    const scoreClass =
        impact_score >= 70 ? 'high' : impact_score >= 40 ? 'mid' : 'low';

    return (
        <div className={`impact-card impact-card--rank-${rank}`}>
            <div className="impact-card__rank">{rank}</div>

            <img
                className="impact-card__avatar"
                src={avatar_url}
                alt={username}
                loading="lazy"
            />

            <div className="impact-card__info">
                <div className="impact-card__username">{username}</div>
                <div className="impact-card__tag">✦ {tag}</div>
            </div>

            <div className="impact-card__score-section">
                <div className={`impact-card__score impact-card__score--${scoreClass}`}>
                    {impact_score}
                </div>
                <div className="impact-card__score-label">Impact Score</div>
            </div>

            <button
                className={`impact-card__expand ${expanded ? 'impact-card__expand--open' : ''}`}
                onClick={() => setExpanded(!expanded)}
                aria-label="Show details"
                id={`expand-${username}`}
            >
                {expanded ? '▲' : '▼'}
            </button>

            {expanded && <StatsBreakdown engineer={engineer} />}
        </div>
    );
}
