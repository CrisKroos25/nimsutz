import { useCallback, useEffect, useRef, useState } from 'react';

/** Carga datos externos y publica únicamente la respuesta de la solicitud vigente. */
export function useAsyncResource(load, initialData, resourceKey = null) {
    const [state, setState] = useState({ data: initialData, loading: true, error: null, load, resourceKey });
    const generation = useRef(0);

    useEffect(() => {
        const request = ++generation.current;
        load().then(
            (data) => {
                if (request === generation.current)
                    setState({ data, loading: false, error: null, load, resourceKey });
            },
            (error) => {
                if (request === generation.current)
                    setState({ data: initialData, loading: false, error, load, resourceKey });
            },
        );
        return () => { generation.current += 1; };
    }, [load, resourceKey, initialData]);

    const reload = useCallback(async () => {
        const request = ++generation.current;
        setState((previous) => ({ ...previous, loading: true, error: null }));
        try {
            const data = await load();
            if (request === generation.current)
                setState({ data, loading: false, error: null, load, resourceKey });
        } catch (error) {
            if (request === generation.current)
                setState({ data: initialData, loading: false, error, load, resourceKey });
        }
    }, [load, resourceKey, initialData]);

    const replace = useCallback((data) => {
        generation.current += 1;
        setState({ data, loading: false, error: null, load, resourceKey });
    }, [load, resourceKey]);

    const pending = state.load !== load || state.resourceKey !== resourceKey;
    return {
        data: pending ? initialData : state.data,
        loading: pending || state.loading,
        error: pending ? null : state.error,
        reload,
        replace,
    };
}
