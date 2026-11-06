import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@shared/auth/AuthContext';

export default function RequireAdministrator() {
    const { user, loading, error } = useAuth();
    if (loading) return <p role="status">Preparando la administración…</p>;
    if (error) return <p role="alert">{error}</p>;
    if (!user || user.role !== 'administrador' || user.account_status !== 'activa' || !user.email_verified) {
        return <Navigate to="/login" replace />;
    }
    return <Outlet />;
}
