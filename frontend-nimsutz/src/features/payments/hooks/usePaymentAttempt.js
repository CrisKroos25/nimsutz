import { useState } from 'react';
import { createPaymentAttempt } from '../paymentAttempt';
import { checkout, getOperationResult } from '../api/paymentsApi';

export default function usePaymentAttempt(scope) {
    const [attempt] = useState(() => createPaymentAttempt({
        storage: sessionStorage, scope, send: checkout, lookup: getOperationResult,
        uuid: () => crypto.randomUUID(),
    }));
    const [pending, setPending] = useState(attempt.key);
    const [hasRequest, setHasRequest] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [fields, setFields] = useState({});

    async function run(body) {
        setBusy(true);
        setError('');
        setFields({});
        try {
            return await (body ? attempt.submit(body) : attempt.recover());
        } catch (error) {
            setError(error.code === 'operation_not_found'
                ? 'Todavía no hay resultado. Consulta nuevamente o reenvía la misma operación con los datos originales.'
                : error.status >= 500 || !error.status
                    ? 'Fallo técnico: no se pudo confirmar el resultado. Consulta el estado o reintenta la misma operación.'
                    : error.message);
            setFields(error.fieldErrors?.card || {});
            return null;
        } finally {
            setPending(attempt.key);
            setHasRequest(attempt.hasRequest);
            setBusy(false);
        }
    }
    return { pending, hasRequest, busy, error, fields, run };
}
