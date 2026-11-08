import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchClient } from '../api/adminClientsApi';
import { getErrorMessage } from '../utils/clientStatus';

/** Detalle de un cliente. reload() refresca desde el servidor sin volver a mostrar el esqueleto. */
export function useAdminClient(clientId) {
    const [state, setState] = useState({ client: null, loading: true, error: null });
    const [reloadKey, setReloadKey] = useState(0);
    const silentRef = useRef(false);

    useEffect(() => {
        const controller = new AbortController();
        if (!silentRef.current) setState({ client: null, loading: true, error: null });
        silentRef.current = false;
        fetchClient(clientId, { signal: controller.signal })
            .then((client) => setState({ client, loading: false, error: null }))
            .catch((err) => {
                if (err?.name === 'AbortError') return;
                setState({ client: null, loading: false, error: getErrorMessage(err, 'No se pudo cargar el cliente.') });
            });
        return () => controller.abort();
    }, [clientId, reloadKey]);

    const reload = useCallback(() => {
        silentRef.current = true;
        setReloadKey((k) => k + 1);
    }, []);

    const retry = useCallback(() => setReloadKey((k) => k + 1), []);
    return { ...state, reload, retry };
}