import { Navigate, Outlet, useLocation } from 'react-router-dom';
import SessionLoader from './SessionLoader';
import SessionError from './SessionError';
import { useAuth } from './AuthContext';

// Ruta de inicio por rol: cada rol tiene su propio "hogar"
export const HOME_BY_ROLE = {
    administrador: '/administration',
    cliente: '/files',
};

export default function RequireRole({ allow }) {
    const { user, loading, error, refresh } = useAuth();
    const location = useLocation();

    if (loading) {
        return <SessionLoader fullScreen message="Verificando permisos…" />;
    }

    if (error) {
        return <SessionError fullScreen message={error} onRetry={refresh} />;
    }

    // 1. Autenticación
    if (!user) {
        return (
            <Navigate
                to="/login"
                replace
                state={{ returnTo: `${location.pathname}${location.search}` }}
            />
        );
    }

    // 2. Estado de la cuenta
    if (user.account_status !== 'activa' || !user.email_verified) {
        return <Navigate to="/login" replace />;
    }

    // 3. Autorización por rol
    if (!allow.includes(user.role)) {
        // Lo mando a SU zona, no a una página genérica
        const home = HOME_BY_ROLE[user.role] ?? '/login';
        return <Navigate to={home} replace />;
    }

    return <Outlet />;
}