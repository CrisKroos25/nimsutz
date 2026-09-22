import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom';
import useTheme from '@shared/hooks/useTheme';
import MainLayout from '@layouts/MainLayout';
import PublicLayout from '@layouts/PublicLayout';
import LandingPage from '../pages/LandingPage';
import DesignSystemPage from '../pages/DesignSystemPage';
import LoginPage from '../pages/LoginPage';

export default function AppRouter() {
    const theme = useTheme();
    return (
        <BrowserRouter>
            <Routes>
                <Route element={<PublicLayout {...theme} />}>
                    <Route index element={<LandingPage />} />
                    <Route path="login" element={<LoginPage />} />
                    <Route
                        path="*"
                        element={
                            <section>
                                <h1>Página no encontrada</h1>
                                <Link to="/">Volver al inicio</Link>
                            </section>
                        }
                    />
                </Route>
                <Route element={<MainLayout {...theme} />}>
                    <Route path="files/*" element={<Navigate to="/login" replace />} />
                    <Route path="trash/*" element={<Navigate to="/login" replace />} />
                    <Route
                        path="design-system"
                        element={<DesignSystemPage />}
                    />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}
