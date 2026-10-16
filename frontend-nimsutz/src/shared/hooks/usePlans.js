import { useCallback, useEffect, useState } from 'react';
import { getPlans, serviceMessage } from '@shared/api/accountApi';

export function usePlans() {
    const [state, setState] = useState({ plans: [], loading: true, error: '' });
    const [attempt, setAttempt] = useState(0);

    useEffect(() => {
        let active = true;
        setState((previous) => ({ ...previous, loading: true, error: '' }));
        getPlans()
            .then((plans) => active && setState({ plans, loading: false, error: '' }))
            .catch((failure) => active && setState({
                plans: [], loading: false,
                error: serviceMessage(failure, 'La consulta de planes'),
            }));
        return () => { active = false; };
    }, [attempt]);

    const reload = useCallback(() => setAttempt((value) => value + 1), []);
    // Para cuando el backend devuelve planes actualizados en otra respuesta (ej. selectPlan)
    const replace = useCallback((plans) => setState({ plans, loading: false, error: '' }), []);

    return { ...state, reload, replace };
}