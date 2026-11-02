import { useEffect, useState } from 'react';
import { AuthContext } from './AuthContext';
import { apiRequest, SESSION_EXPIRED_EVENT } from '../api/httpClient';
import { clearDeletedAccountData } from './deletedAccountData';
import { deleteOwnAccount, withAccountDestination } from '../api/accountApi';
import { clearPlanPreference, sessionDestination } from './accessFlow';

export default function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [destination, setDestination] = useState('/files');
    const [deletionNotice, setDeletionNotice] = useState(null);
    async function refresh() {
        setLoading(true);
        try {
            const data = await withAccountDestination(await apiRequest('/api/auth/session/'));
            setUser(data.user);
            setDestination(sessionDestination(data));
            setError(data.accessError || '');
        } catch {
            setError('No se pudo conectar con el servicio. Inténtalo de nuevo.');
        } finally { setLoading(false); }
    }
    useEffect(() => {
        let active = true;
        apiRequest('/api/auth/session/').then(withAccountDestination).then((data) => {
            if (active) { setUser(data.user); setDestination(sessionDestination(data)); setError(data.accessError || ''); }
        }).catch(() => {
            if (active) setError('No se pudo conectar con el servicio. Inténtalo de nuevo.');
        }).finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, []);
    useEffect(() => {
        // httpClient confirmó con el servidor que la sesión murió (por ejemplo, por una suspensión).
        // Se limpia el estado igual que en signOut y RequireSession redirige a /login.
        function onSessionExpired() {
            clearPlanPreference();
            setUser(null);
            setDestination('/files');
            setError('');
        }
        window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
        return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    }, []);
    async function signIn(email, password) {
        const data = await apiRequest('/api/auth/login/', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const account = await withAccountDestination(data);
        setDeletionNotice(null);
        setUser(account.user);
        setDestination(sessionDestination(account));
        setError(account.accessError || '');
    }
    async function signOut() {
        await apiRequest('/api/auth/logout/', { method: 'POST' });
        clearPlanPreference();
        setUser(null);
        setDestination('/files');
        setError('');
    }
    async function removeAccount() {
        const result = await deleteOwnAccount();
        clearDeletedAccountData(user.id);
        setDeletionNotice({ pending: result.deletion_pending });
        setUser(null);
        setDestination('/files');
        setError('');
        return result;
    }
    return <AuthContext.Provider value={{ user, loading, error, destination, refresh, signIn, signOut, removeAccount, deletionNotice, clearDeletionNotice: () => setDeletionNotice(null) }}>{children}</AuthContext.Provider>;
}