import { useState, useEffect } from 'react';
import { agent0Client, MetricsResponse } from '../api/agent0';

export const useMetrics = (intervalMs: number = 5000) => {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setIsLoading(true);
        const data = await agent0Client.getHealth();
        setMetrics(data);
        setError(null);
      } catch (err) {
        setError(err as Error);
      } finally {
        setIsLoading(false);
      }
    };

    // Initial fetch
    fetchMetrics();

    // Set up polling
    const interval = setInterval(fetchMetrics, intervalMs);

    return () => clearInterval(interval);
  }, [intervalMs]);

  return { metrics, isLoading, error };
}; 