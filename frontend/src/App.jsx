import './App.css';
import { Leaderboard } from './components/Leaderboard';
import { useEngineers } from './hooks/useEngineers';
import { formatNumber } from './utils/formatters';

function App() {
  const { engineers, meta, loading, error } = useEngineers(90);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__badge">
          <span>●</span> Live from GitHub
        </div>
        <h1 className="app-header__title">PostHog Impact Index</h1>
        <p className="app-header__subtitle">
          Top 5 most impactful engineers over the last 90 days, ranked by
          contribution quality, collaboration depth, and knowledge breadth.
        </p>

        {meta && (
          <div className="app-meta">
            <div className="app-meta__item">
              📊 <span>{formatNumber(meta.total_prs_analyzed)}</span> PRs analyzed
            </div>
            <div className="app-meta__item">
              💬 <span>{formatNumber(meta.total_comments_analyzed)}</span> review comments
            </div>
            <div className="app-meta__item">
              🏢 <span>{meta.repo}</span>
            </div>
          </div>
        )}
      </header>

      <Leaderboard engineers={engineers} loading={loading} error={error} />
    </div>
  );
}

export default App;
