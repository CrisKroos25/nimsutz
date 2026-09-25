import AuthProvider from '@shared/auth/AuthProvider';
import RequireSession from '@shared/auth/RequireSession';
import AboutPage from '../pages/AboutPage';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import useTheme from '@shared/hooks/useTheme';
import MainLayout from '@layouts/MainLayout';
import PublicLayout from '@layouts/PublicLayout';
import LandingPage from '../pages/LandingPage';
import DesignSystemPage from '../pages/DesignSystemPage';
import LoginPage from '../pages/LoginPage';
import { FilesPage } from '@features/files/pages/FilePages';
import TrashPage from '@features/files/transfers/components/TrashView/Trash';

export default function AppRouter() {
    const theme = useTheme();
    return (
        <BrowserRouter>
            <AuthProvider>
                <Routes>
                    <Route element={<PublicLayout {...theme} />}>
                        <Route index element={<LandingPage />} />
                        <Route path="login" element={<LoginPage />} />
                        <Route path="about" element={<AboutPage />} />
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
                        <Route element={<RequireSession />}>
                            <Route path="files/*" element={<FilesPage />} />
                            {/* TrashPage es entregable de B (Rodrigo), página autónoma en
                                src/features/files/trash/. Placeholder mientras no exista:
                                cuando la entregue, import { TrashPage } from
                                '@features/files/trash/TrashPage'; y reemplazar aquí. */}
                            <Route path="trash/*" element={<TrashPage />} />
                        </Route>
                        <Route path="design-system" element={<DesignSystemPage />} />
                    </Route>
                </Routes>
            </AuthProvider>
        </BrowserRouter>
    );
}
