import { useState } from 'react';
import { useAuth } from '@shared/auth/AuthContext';
import { Link, Navigate } from 'react-router-dom';
import Input from '../shared/components/Input/Input';
import Button from '../shared/components/Button/Button';
import styles from './LoginPage.module.css';

export default function LoginPage() {
    const { user, loading, signIn } = useAuth();
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    async function submit(event) {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        setBusy(true);
        setError('');
        try { await signIn(data.get('email').trim(), data.get('password')); }
        catch (failure) { setError(failure.message); }
        finally { setBusy(false); }
    }
    if (user) return <Navigate to="/files" replace />;
    return (
        <section className={styles.page} aria-labelledby="login-title">
            <p>BIENVENIDO A NIM SUTZ’</p>
            <h1 id="login-title">Inicia sesión en tu espacio</h1>
            <form onSubmit={submit}>
                <Input label="Correo electrónico" type="email" autoComplete="username" name="email" maxLength={254} required disabled={busy || loading} />
                <Input label="Contraseña" type="password" autoComplete="current-password" name="password" maxLength={128} required disabled={busy || loading} />
                {error && <p role="alert">{error}</p>}
                <Button type="submit" loading={busy} disabled={loading}>Iniciar sesión</Button>
            </form>
            <p>¿Aún no tienes cuenta? <span role="link" aria-disabled="true" className={styles.register}>Registrarse</span></p>
            <Link to="/">Volver al inicio</Link>
        </section>
    );
}
