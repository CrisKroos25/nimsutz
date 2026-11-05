import { Navigate, Outlet, useLocation } from 'react-router-dom';
import SessionLoader from './SessionLoader';
import SessionError from './SessionError';
import { useAuth } from './AuthContext';

/**
 * Guardia de ruta para vistas administrativas (M19 - Rodrigo).
 * Solo permite el acceso a usuarios autenticados con rol de 'administrador'.
 */
export default function RequireAdmin() {
    const { user, loading, error, refresh } = useAuth();
    const location = useLocation();

    if (loading) {
        return <SessionLoader fullScreen message="Verificando permisos de administración…" />;
    }

    if (error) {
        return <SessionError fullScreen message={error} onRetry={refresh} />;
    }

    if (!user) {
        return <Navigate to="/login" replace state={{ returnTo: location.pathname }} />;
    }

    if (user.role !== 'administrador') {
        return <Navigate to="/files" replace />;
    }

    return <Outlet />;
}

