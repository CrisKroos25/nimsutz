import { Navigate, Outlet, useLocation } from 'react-router-dom';
import Button from '../components/Button/Button';
import { useAuth } from './AuthContext';
export default function RequireSession() {
    const { user, loading, error, refresh, destination } = useAuth();
    const location = useLocation();
    if (loading) return <p role="status">Comprobando sesión…</p>;
    if (error) return <div role="alert">{error} <Button onClick={refresh}>Reintentar</Button></div>;
    if (!user) return <Navigate to="/login" replace state={{ returnTo: location.pathname }} />;
    if (destination.startsWith('/plans') && /^\/(files|trash)(\/|$)/.test(location.pathname)) {
        return <Navigate to={destination} replace />;
    }
    return <Outlet />;
}
