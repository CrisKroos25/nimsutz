// Solo persiste la clave. Los datos de tarjeta permanecen en memoria durante el intento.
export function createPaymentAttempt({ storage, scope, send, lookup, uuid }) {
    const slot = `payment-attempt:${scope}`;
    let key = storage.getItem(slot);
    let request;
    let busy = false;
    return {
        get key() { return key; },
        get hasRequest() { return Boolean(request); },
        async submit(body) {
            if (busy) return null;
            busy = true;
            const wasPending = Boolean(key);
            try {
                if (!key) {
                    const nextKey = uuid();
                    storage.setItem(slot, nextKey);
                    key = nextKey;
                }
                request ||= body;
                const result = await send(key, request);
                storage.removeItem(slot);
                key = null;
                request = null;
                return result;
            } catch (error) {
                if (!wasPending && error.status === 400 && error.code === 'invalid_request') {
                    storage.removeItem(slot);
                    key = null;
                    request = null;
                }
                throw error;
            } finally { busy = false; }
        },
        async recover() {
            if (busy || !key) return null;
            busy = true;
            try {
                const result = await lookup(key);
                storage.removeItem(slot);
                key = null;
                request = null;
                return result;
            } finally { busy = false; }
        },
    };
}
