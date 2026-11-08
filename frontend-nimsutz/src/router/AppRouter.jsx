import AuthProvider from '@shared/auth/AuthProvider';
import RequireSession from '@shared/auth/RequireSession';
import RequireAdmin from '@shared/auth/RequireAdmin';
import RequireRole from '@shared/auth/RequireRole';
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom';
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
import FilesGate from '@shared/auth/FilesGate';
import TrashPage from '@features/files/pages/Trash';
import ForgotPassword from '@features/auth/pages/ForgotPassword';
import ResetPassword from '@features/auth/pages/ResetPassword';
import VerifyEmail from '@features/auth/pages/VerifyEmail';
import { CheckoutPage, PaymentResultPage } from '@features/payments/PaymentPages';
import { PaymentHistoryPage, PaymentDetailPage } from '@features/payments/history/PaymentHistoryPages';
import { SubscriptionPage, RenewPage, ChangePlanPage } from '@features/subscription/SubscriptionPages';
import { AdministrationDashboardPage, AdministrationPaymentsPage, AdministrationPaymentDetailPage } from '@features/administration/AdministrationPages';
import AdminPlansPage from '@features/administration/plans/AdminPlansPage';
import AuditPage from '@features/administration/audit/AuditPage';

export default function AppRouter() {
    const theme = useTheme();
    return (
        <BrowserRouter>
            <AuthProvider>
                <Routes>

                    <Route element={<PublicLayout {...theme} />}>
                        <Route index element={<LandingPage />} />
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

                    <Route path="register" element={<RegisterPage {...theme} />} />
                    <Route element={<AuthLayout {...theme} />}>
                        <Route path="login" element={<LoginPage />} />
                        <Route path="verify-email" element={<VerifyEmail />} />
                        <Route path="forgot-password" element={<ForgotPassword />} />
                        <Route path="reset-password" element={<ResetPassword />} />
                    </Route>
                    
                    <Route element={<RequireSession />}>
                        <Route element={<RequireRole allow={['cliente']} />}>
                            <Route element={<MainLayout {...theme} />}>
                                <Route path="/files" element={<FilesGate><FilesPage /></FilesGate>} />
                                <Route path="trash/*" element={<TrashPage />} />
                                <Route path="profile" element={<ProfilePage />} />
                                <Route path="plans" element={<PlansPage />} />
                                <Route path="plans/summary" element={<PlansPage />} />
                                <Route path="payments/checkout/:quoteId" element={<CheckoutPage />} />
                                <Route path="payments/result/:paymentId" element={<PaymentResultPage />} />
                                <Route path="payments/history" element={<PaymentHistoryPage />} />
                                <Route path="payments/history/:paymentId" element={<PaymentDetailPage />} />
                                <Route path="subscription" element={<SubscriptionPage />} />
                                <Route path="subscription/renew" element={<RenewPage />} />
                                <Route path="subscription/change" element={<ChangePlanPage />} />
                            </Route>
                        </Route>
                    </Route>
                            
                    <Route element={<RequireSession />}>
                        <Route element={<RequireRole allow={['administrador']} />}>
                            <Route path="administration" element={<AdministrationDashboardPage />} />
                            <Route path="administration/payments" element={<AdministrationPaymentsPage />} />
                            <Route path="administration/payments/:paymentId" element={<AdministrationPaymentDetailPage />} />
                            <Route path="administration/plans" element={<AdminPlansPage />} />
                            <Route path="administration/audit" element={<AuditPage />} />
                        </Route>
                    </Route>


                </Routes>
            </AuthProvider>
        </BrowserRouter>
    );
}
