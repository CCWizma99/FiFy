import { useEffect, useState } from 'react';

// The key hides stale data immediately; cleanup also guards uncancellable responses.
export default function useRequest(key, load, delay = 0) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState(null);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const data = await load(controller.signal);
        if (active) setState({ key, attempt, load, data });
      } catch (error) {
        if (active) setState({ key, attempt, load, error });
      }
    }, delay);
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [key, attempt, load, delay]);
  const current = state?.key === key && state?.attempt === attempt && state?.load === load ? state : null;
  return { data: current?.data, error: current?.error, loading: !current, retry: () => setAttempt(n => n + 1) };
}
