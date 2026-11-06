import { Navigate, Outlet, useLocation } from 'react-router-dom';

import SessionLoader from './SessionLoader';
import SessionError from './SessionError';
import { useAuth } from './AuthContext';

export default function RequireAdmin() {
    const { user, loading, error, refresh } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <SessionLoader
                fullScreen
                message="Verificando permisos de administración…"
            />
        );
    }

    if (error) {
        return (
            <SessionError
                fullScreen
                message={error}
                onRetry={refresh}
            />
        );
    }

    // 1. Autenticación
    if (!user) {
        return (
            <Navigate
                to="/login"
                replace
                state={{
                    returnTo: `${location.pathname}${location.search}`
                }}
            />
        );
    }

    // 2. Autorización por rol
    if (user.role !== 'administrador') {
        return <Navigate to="/files" replace />;
    }

    // 3. Estado de la cuenta
    if (
        user.account_status !== 'activa' ||
        !user.email_verified
    ) {
        return <Navigate to="/login" replace />;
    }

    return <Outlet />;
}