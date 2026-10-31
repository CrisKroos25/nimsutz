import { useEffect, useRef, useState } from 'react';
import { Mail } from 'lucide-react';
import Brand from '@layouts/Brand';
import PasswordInput from '@shared/components/Input/PasswordInput';
import { fieldMessage } from '@shared/auth/accessFlow';
import { useAuth } from '@shared/auth/AuthContext';
import { Link, Navigate, useLocation } from 'react-router-dom';
import Input from '../shared/components/Input/Input';
import Button from '../shared/components/Button/Button';
import styles from './LoginPage.module.css';
import SessionLoader from '@shared/auth/SessionLoader';

export default function LoginPage() {
    const { user, loading, signIn, destination, deletionNotice, clearDeletionNotice } = useAuth();
    const location = useLocation();
    const submitting = useRef(false);
    const errorMessage = useRef(null);
    const [errors, setErrors] = useState({});
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    useEffect(() => { if (error && !busy) errorMessage.current?.focus(); }, [error, busy]);
    async function submit(event) {
        event.preventDefault();
        if (submitting.current) return;
        submitting.current = true;
        const data = new FormData(event.currentTarget);
        setBusy(true);
        setError('');
        setErrors({});
        try { await signIn(data.get('email').trim(), data.get('password')); }
        catch (failure) { setError(failure.message); setErrors(failure.fieldErrors || {}); }
        finally { submitting.current = false; setBusy(false); }
    }
    if (loading) return <SessionLoader />;
    const returnTo = ['/profile', '/plans', '/plans/summary', '/trash', '/files'].includes(location.state?.returnTo) ? location.state.returnTo : null;
    if (user) return <Navigate to={destination === '/files' && returnTo ? returnTo : destination} replace />;
    return (
        <section className={styles.page} aria-labelledby="login-title">
            <header className={styles.loginHeading}>
                <Brand showName={false} className={styles.logo} />
                <h1 id="login-title">Bienvenido a <span className={styles.brandName}>Nim sutz’</span></h1>
                <p>Gestión documental en la nube</p>
            </header>
            {deletionNotice && <div className={styles.notice} role="status">
                <strong>Tu cuenta se eliminó.</strong>
                <p>{deletionNotice.pending ? 'Estamos terminando de borrar tus archivos. No necesitas hacer nada más.' : 'Todos los datos de tu cuenta se borraron.'}</p>
                <p>Puedes crear una cuenta nueva con el mismo correo y empezar desde cero.</p>
            </div>}
            <form onSubmit={submit}>
                <Input label="Correo electrónico" type="email" placeholder="tu@correo.com" leadingIcon={<Mail size={18} />} autoComplete="username" name="email" maxLength={254} required disabled={busy || loading} error={fieldMessage(errors.email)} />
                <PasswordInput label="Contraseña" placeholder="Tu contraseña" autoComplete="current-password" name="password" maxLength={128} required disabled={busy || loading} error={fieldMessage(errors.password)} />
                <p className={styles.recovery}><Link to="/forgot-password">Olvidé mi contraseña</Link></p>
                {error && <p ref={errorMessage} tabIndex={-1} role="alert" className={styles.error}>{error}</p>}
                <Button type="submit" loading={busy} disabled={loading}>Ingresar</Button>
            </form>
            <p className={styles.switchPage}>¿Aún no tienes cuenta? <Link to="/register" onClick={clearDeletionNotice}>Crear cuenta</Link></p>
        </section>
    );
}
