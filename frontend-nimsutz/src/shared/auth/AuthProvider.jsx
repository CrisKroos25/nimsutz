import { useEffect, useState } from 'react';
import { AuthContext } from './AuthContext';
import { apiRequest } from '../api/httpClient';

export default function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    async function refresh() {
        try {
            const data = await apiRequest('/api/auth/session/');
            setUser(data.user);
            setError('');
        } catch {
            setUser(null);
            setError('No se pudo conectar con el servicio. Inténtalo de nuevo.');
        } finally { setLoading(false); }
    }
    useEffect(() => {
        let active = true;
        apiRequest('/api/auth/session/').then((data) => {
            if (active) { setUser(data.user); setError(''); }
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
        setUser(data.user);
        setError('');
    }
    async function signOut() {
        await apiRequest('/api/auth/logout/', { method: 'POST' });
        setUser(null);
    }
    return <AuthContext.Provider value={{ user, loading, error, refresh, signIn, signOut }}>{children}</AuthContext.Provider>;
}
