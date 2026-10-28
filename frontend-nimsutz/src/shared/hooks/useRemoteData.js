import { useCallback, useEffect, useState } from 'react';

// Carga datos del servidor sin dejar ver resultados de una consulta anterior.
// `load` debe estar memorizada (useCallback): cuando cambia, se vuelve a consultar.
export function useRemoteData(load) {
    const [attempt, setAttempt] = useState(0);
    const [state, setState] = useState({ load: null, attempt: -1, data: null, error: null });

    useEffect(() => {
        let active = true;
        load()
            .then((data) => { if (active) setState({ load, attempt, data, error: null }); })
            .catch((error) => { if (active) setState({ load, attempt, data: null, error }); });
        return () => { active = false; };
    }, [load, attempt]);

    const reload = useCallback(() => setAttempt((value) => value + 1), []);
    const settled = state.load === load && state.attempt === attempt;
    return {
        loading: !settled,
        data: settled ? state.data : null,
        error: settled ? state.error : null,
        reload,
    };
}
