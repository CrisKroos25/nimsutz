import { Navigate } from 'react-router-dom';
import { useHasSubscription } from '@shared/hooks/useHasSubscription';

// Protege las rutas que requieren una suscripción activa.
export default function FilesGate({ children }) {
    const hasSubscription = useHasSubscription();
    if (hasSubscription === null) return null;
    return hasSubscription ? children : <Navigate to="/plans" replace />;
}