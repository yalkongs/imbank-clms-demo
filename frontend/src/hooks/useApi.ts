import { useState, useEffect, useCallback } from 'react';
import { AxiosResponse } from 'axios';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

interface UseApiReturn<T> extends UseApiState<T> {
  refetch: () => Promise<void>;
}

/**
 * API 호출 훅
 */
export function useApi<T>(
  apiCall: () => Promise<AxiosResponse<T>>,
  deps: any[] = []
): UseApiReturn<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const response = await apiCall();
      setState({ data: response.data, loading: false, error: null });
    } catch (error) {
      setState({ data: null, loading: false, error: error as Error });
    }
  }, deps);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    ...state,
    refetch: fetchData,
  };
}

/**
 * 지연 API 호출 훅 (수동 트리거)
 */
export function useLazyApi<T, P = any>(
  apiCall: (params: P) => Promise<AxiosResponse<T>>
): [
  (params: P) => Promise<T | null>,
  UseApiState<T>
] {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (params: P) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const response = await apiCall(params);
      setState({ data: response.data, loading: false, error: null });
      return response.data;
    } catch (error) {
      setState({ data: null, loading: false, error: error as Error });
      return null;
    }
  }, [apiCall]);

  return [execute, state];
}

/**
 * 폴링 API 훅 (주기적 갱신)
 */
export function usePollingApi<T>(
  apiCall: () => Promise<AxiosResponse<T>>,
  interval: number = 30000,
  deps: any[] = []
): UseApiReturn<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    try {
      const response = await apiCall();
      setState({ data: response.data, loading: false, error: null });
    } catch (error) {
      setState(prev => ({ ...prev, loading: false, error: error as Error }));
    }
  }, deps);

  useEffect(() => {
    fetchData();

    const intervalId = setInterval(fetchData, interval);

    return () => clearInterval(intervalId);
  }, [fetchData, interval]);

  return {
    ...state,
    refetch: fetchData,
  };
}

export default useApi;
