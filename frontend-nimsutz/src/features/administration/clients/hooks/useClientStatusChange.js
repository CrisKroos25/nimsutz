import { useCallback, useRef, useState } from 'react';
import { reactivateClient, suspendClient } from '../api/adminClientsApi';
import { getErrorMessage } from '../utils/clientStatus';

/**
 * Suspender / reactivar. El ref bloquea el reenvío aunque el usuario haga doble clic
 * antes de que React pinte `busy`.
 * onDone(result, action) se llama solo si el servidor respondió con éxito.
 */
export function useClientStatusChange(clientId, onDone) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const busyRef = useRef(false);

    const run = useCallback(
        async (action) => {
            if (busyRef.current) return;
            busyRef.current = true;
            setBusy(true);
            setError(null);
            try {
                const call = action === 'suspend' ? suspendClient : reactivateClient;
                const result = await call(clientId);
                onDone?.(result, action);
            } catch (err) {
                setError(getErrorMessage(err));
            } finally {
                busyRef.current = false;
                setBusy(false);
            }
        },
        [clientId, onDone],
    );

    const clearError = useCallback(() => setError(null), []);
    return { run, busy, error, clearError };
}