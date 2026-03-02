import { ShimmerCard } from './ShimmerCard';
import { ImpactCard } from './ImpactCard';

export function Leaderboard({ engineers, loading, error }) {
    if (error) {
        return (
            <div className="app-error">
                <h3>⚠ Failed to load data</h3>
                <p>{error}</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="leaderboard">
                {Array.from({ length: 5 }).map((_, i) => (
                    <ShimmerCard key={i} />
                ))}
            </div>
        );
    }

    return (
        <div className="leaderboard">
            {engineers.map((eng) => (
                <ImpactCard key={eng.username} engineer={eng} />
            ))}
        </div>
    );
}
