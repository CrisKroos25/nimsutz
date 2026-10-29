import { Navigate, Outlet, useLocation } from 'react-router-dom';
import Button from '../components/Button/Button';
import SessionLoader from './SessionLoader';
import SessionError from './SessionError';
import { useAuth } from './AuthContext';

export default function RequireSession() {
    const { user, loading, error, refresh, destination } = useAuth();
    const location = useLocation();
    if (loading) return <SessionLoader fullScreen message="Preparando tu espacio…" />;
    if (error) return <SessionError fullScreen message={error} onRetry={refresh} />;
    if (!user) return <Navigate to="/login" replace state={{ returnTo: location.pathname }} />;
    if (destination.startsWith('/plans') && /^\/(files|trash)(\/|$)/.test(location.pathname)) {
        return <Navigate to={destination} replace />;
    }
    return <Outlet />;
}
