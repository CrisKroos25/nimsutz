import { useEffect, useState } from 'react';
import { AuthContext } from './AuthContext';
import { apiRequest } from '../api/httpClient';
import { withAccountDestination } from '../api/accountApi';
import { clearPlanPreference, sessionDestination } from './accessFlow';

export default function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [destination, setDestination] = useState('/files');
    async function refresh() {
        try {
            const data = await withAccountDestination(await apiRequest('/api/auth/session/'));
            setUser(data.user);
            setDestination(sessionDestination(data));
            setError('');
        } catch {
            setUser(null);
            setError('No se pudo conectar con el servicio. Inténtalo de nuevo.');
        } finally { setLoading(false); }
    }
    useEffect(() => {
        let active = true;
        apiRequest('/api/auth/session/').then(withAccountDestination).then((data) => {
            if (active) { setUser(data.user); setDestination(sessionDestination(data)); setError(''); }
        }).catch(() => {
            if (active) setError('No se pudo conectar con el servicio. Inténtalo de nuevo.');
        }).finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, []);
    async function signIn(email, password) {
        const data = await apiRequest('/api/auth/login/', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const account = await withAccountDestination(data);
        setUser(account.user);
        setDestination(sessionDestination(account));
        setError('');
    }
    async function signOut() {
        await apiRequest('/api/auth/logout/', { method: 'POST' });
        clearPlanPreference();
        setUser(null);
        setDestination('/files');
    }
    return <AuthContext.Provider value={{ user, loading, error, destination, refresh, signIn, signOut }}>{children}</AuthContext.Provider>;
}
