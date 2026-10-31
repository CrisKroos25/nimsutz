// @features/files/hooks/useUploadRules.js
import { useEffect, useState } from 'react';
import { transfersApi } from '@features/files/api/transfersApi';

let rulesPromise = null;

// Se consulta una sola vez; si falla, se reintenta en el siguiente uso.
export function loadRules() {
    rulesPromise ??= transfersApi.obtenerReglas().catch(() => {
        rulesPromise = null;
        return null;
    });
    return rulesPromise;
}

// Para componentes que quieran mostrar el límite o los tipos permitidos.
export function useUploadRules() {
    const [rules, setRules] = useState(null);
    useEffect(() => {
        let active = true;
        loadRules().then((value) => active && setRules(value));
        return () => { active = false; };
    }, []);
    return rules; // null mientras carga o si falló
}