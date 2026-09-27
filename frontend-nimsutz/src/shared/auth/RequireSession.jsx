import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';
export default function RequireSession() {
    const { user, loading, error, refresh } = useAuth();
    if (loading) return <p role="status">Comprobando sesión…</p>;
    if (error) return <div role="alert">{error} <button onClick={refresh}>Reintentar</button></div>;
    return user ? <Outlet /> : <Navigate to="/login" replace />;
}
