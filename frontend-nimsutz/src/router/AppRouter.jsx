import AuthProvider from '@shared/auth/AuthProvider';
import RequireSession from '@shared/auth/RequireSession';
import AboutPage from '../pages/AboutPage';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import useTheme from '@shared/hooks/useTheme';
import MainLayout from '@layouts/MainLayout';
import PublicLayout from '@layouts/PublicLayout';
import AuthLayout from '@layouts/AuthLayout';
import LandingPage from '../pages/LandingPage';
import LoginPage from '../pages/LoginPage';
import ProfilePage from '../pages/ProfilePage';
import RegisterPage from '../pages/RegisterPage';
import PlansPage from '../pages/PlansPage';
import { FilesPage } from '@features/files/pages/FilePages';
import TrashPage from '@features/files/pages/Trash';
import ForgotPassword from '@features/auth/pages/ForgotPassword';
import ResetPassword from '@features/auth/pages/ResetPassword';

export default function AppRouter() {
    const theme = useTheme();
    return (
        <BrowserRouter>
            <AuthProvider>
                <Routes>
                    <Route element={<PublicLayout {...theme} />}>
                        <Route index element={<LandingPage />} />
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
                    <Route element={<AuthLayout {...theme} />}>
                        <Route path="login" element={<LoginPage />} />
                        <Route path="register" element={<RegisterPage />} />
                        <Route path="forgot-password" element={<ForgotPassword />} />
                        <Route path="reset-password" element={<ResetPassword />} />
                    </Route>
                    <Route element={<MainLayout {...theme} />}>
                        <Route element={<RequireSession />}>
                            <Route path="files/*" element={<FilesPage />} />
                            <Route path="trash/*" element={<TrashPage />} />
                            <Route path="profile" element={<ProfilePage />} />
                            <Route path="plans" element={<PlansPage />} />
                            <Route path="plans/summary" element={<PlansPage />} />
                        </Route>
                    </Route>
                </Routes>
            </AuthProvider>
        </BrowserRouter>
    );
}
