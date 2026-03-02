import { useState, useEffect, useRef } from 'react';

const API_BASE = '/api';
const POLL_INTERVAL = 3000;

export function useEngineers(days = 90) {
    const [engineers, setEngineers] = useState([]);
    const [meta, setMeta] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const timerRef = useRef(null);

    useEffect(() => {
        let cancelled = false;

        const fetchData = () => {
            fetch(`${API_BASE}/engineers?days=${days}`)
                .then((res) => {
                    if (cancelled) return;
                    if (res.status === 202) {
                        setLoading(true);
                        setError(null);
                        timerRef.current = setTimeout(fetchData, POLL_INTERVAL);
                        return;
                    }
                    if (!res.ok) throw new Error(`HTTP ${res.status}`);
                    return res.json().then((data) => {
                        if (cancelled) return;
                        setEngineers(data.engineers || []);
                        setMeta(data.meta || null);
                        setLoading(false);
                        setError(null);
                    });
                })
                .catch((err) => {
                    if (cancelled) return;
                    setError(err.message);
                    setLoading(false);
                });
        };

        setLoading(true);
        setError(null);
        fetchData();

        return () => {
            cancelled = true;
            clearTimeout(timerRef.current);
        };
    }, [days]);

    return { engineers, meta, loading, error };
}
