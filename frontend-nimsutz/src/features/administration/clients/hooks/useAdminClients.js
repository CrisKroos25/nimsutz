import { useCallback, useEffect, useState } from 'react';
import { fetchClients } from '../api/adminClientsApi';
import { getErrorMessage } from '../utils/clientStatus';

/** Lista paginada de clientes. Cancela la petición anterior al cambiar filtros o página. */
export function useAdminClients({ search, status, planCode, page }) {
    const [state, setState] = useState({ data: null, loading: true, error: null });
    const [reloadKey, setReloadKey] = useState(0);

    useEffect(() => {
        const controller = new AbortController();
        setState((prev) => ({ ...prev, loading: true, error: null }));
        fetchClients({ search, status, planCode, page }, { signal: controller.signal })
            .then((data) => setState({ data, loading: false, error: null }))
            .catch((err) => {
                if (err?.name === 'AbortError') return;
                setState({ data: null, loading: false, error: getErrorMessage(err, 'No se pudo cargar la lista de clientes.') });
            });
        return () => controller.abort();
    }, [search, status, planCode, page, reloadKey]);

    const reload = useCallback(() => setReloadKey((k) => k + 1), []);
    return { ...state, reload };
}