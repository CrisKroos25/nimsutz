import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '@shared/auth/AuthContext';
import { getSubscription, validateSubscription } from '@shared/api/accountApi';

// Devuelve: true (tiene suscripción), false (no tiene) o null (todavía no se sabe).
export function useHasSubscription() {
    const { user } = useAuth();
    const { pathname } = useLocation();
    const [hasSubscription, setHasSubscription] = useState(null);

    useEffect(() => {
        let active = true;
        getSubscription()
            .then((response) => {
                if (active) setHasSubscription(Boolean(validateSubscription(response)));
            })
            .catch(() => {
                // Si falla la consulta, no ocultamos nada: el backend sigue protegiendo las operaciones.
                if (active) setHasSubscription(null);
            });
        return () => { active = false; };
    }, [user?.id, pathname]);

    return hasSubscription;
}