import AuthProvider from '@shared/auth/AuthProvider';
import RequireSession from '@shared/auth/RequireSession';
import AboutPage from '../pages/AboutPage';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import useTheme from '@shared/hooks/useTheme';
import MainLayout from '@layouts/MainLayout';
import PublicLayout from '@layouts/PublicLayout';
import LandingPage from '../pages/LandingPage';
import LoginPage from '../pages/LoginPage';
import { FilesPage } from '@features/files/pages/FilePages';
import TrashPage from '@features/files/pages/Trash';

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
                            <Route path="trash/*" element={<TrashPage />} />
                        </Route>
                    </Route>
                </Routes>
            </AuthProvider>
        </BrowserRouter>
    );
}
