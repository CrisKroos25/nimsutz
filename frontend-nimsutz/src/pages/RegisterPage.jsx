import { useEffect, useRef, useState } from 'react';
import { Check, Circle, Mail, UserRound } from 'lucide-react';
import PasswordInput from '@shared/components/Input/PasswordInput';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '@shared/auth/AuthContext';
import { fieldMessage, readPlanPreference, validateRegistration, passwordRequirements } from '@shared/auth/accessFlow';
import { registerAccount, serviceMessage } from '@shared/api/accountApi';
import Input from '@shared/components/Input/Input';
import Button from '@shared/components/Button/Button';
import { verificationApi } from '@features/auth/api/verificationApi';
import styles from './LoginPage.module.css';

export default function RegisterPage() {
    const { user, loading, destination } = useAuth();
    const submitting = useRef(false);
    const resultHeading = useRef(null);
    const errorMessage = useRef(null);
    const [resendMessage, setResendMessage] = useState('');
    const [cooldown, setCooldown] = useState(0);
    const [busy, setBusy] = useState(false);
    const [errors, setErrors] = useState({});
    const [error, setError] = useState('');
    const [registered, setRegistered] = useState(null);
    const [password, setPassword] = useState('');
    const [confirmation, setConfirmation] = useState('');
    const requirements = passwordRequirements(password);
    const matches = confirmation.length > 0 && confirmation === password;

    useEffect(() => { if (registered) resultHeading.current?.focus(); }, [registered]);
    useEffect(() => { if (error && !busy) errorMessage.current?.focus(); }, [error, busy]);
    useEffect(() => {
        if (cooldown <= 0) return;
        const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
        return () => clearTimeout(timer);
    }, [cooldown]);

    async function resend() {
        if (submitting.current || cooldown > 0) return;
        submitting.current = true;
        setBusy(true);
        setError('');
        setResendMessage('');
        try {
            await verificationApi.resendVerification(registered.email);
            setResendMessage('Solicitud aceptada. Revisa tu bandeja y la carpeta de spam; usa el enlace más reciente.');
            setCooldown(30);
        } catch (failure) {
            setError(serviceMessage(failure, 'El reenvío de verificación'));
        } finally { submitting.current = false; setBusy(false); }
    }

    function updatePassword(event) {
        setPassword(event.target.value);
        setErrors((previous) => ({ ...previous, password: undefined, password_confirmation: undefined }));
    }

    function updateConfirmation(event) {
        setConfirmation(event.target.value);
        setErrors((previous) => ({ ...previous, password_confirmation: undefined }));
    }

    async function submit(event) {
        event.preventDefault();
        if (submitting.current) return;
        const form = event.currentTarget;
        const values = Object.fromEntries(new FormData(form));
        const invalid = validateRegistration(values);
        setErrors(invalid);
        setError('');
        if (Object.keys(invalid).length) {
            form.elements.namedItem(Object.keys(invalid)[0])?.focus();
            return;
        }
        submitting.current = true;
        setBusy(true);
        try {
            const preference = readPlanPreference();
            const result = await registerAccount({ ...values, name: values.name.trim(), email: values.email.trim(),
                ...(preference ? { preferred_plan_version_id: preference } : {}) });
            if (result?.status !== 'pending_verification') throw new Error('No se pudo confirmar el registro. Intenta iniciar sesión antes de repetirlo.');
            // La preferencia se conserva hasta que el endpoint autenticado confirme su guardado.
            setRegistered({ email: values.email.trim(), emailSent: result.email_sent === true });
            setPassword('');
            setConfirmation('');
            form.reset();
        } catch (failure) {
            setErrors(failure.fieldErrors || {});
            setError(serviceMessage(failure, 'El registro'));
        } finally { submitting.current = false; setBusy(false); }
    }

    if (loading) return <p role="status">Comprobando sesión…</p>;
    if (user) return <Navigate to={destination} replace />;
    return <section className={styles.page} aria-labelledby="register-title">
        <header className={styles.registerHeading}>
            <h1 id="register-title">Crear cuenta</h1>
            {!registered && <p>Tu espacio para organizar y guardar documentos.</p>}
        </header>
        {registered ? <div className={styles.notice} role="status">
            <h2 ref={resultHeading} tabIndex={-1}>Cuenta pendiente de verificación</h2>
            <p>{registered.emailSent ? `Enviamos un enlace a ${registered.email}. Revisa tu correo para verificar la cuenta.` : `La cuenta ${registered.email} está creada, pero no pudimos confirmar el envío del correo. La verificación sigue pendiente.`}</p>
            <p>Después de verificar, inicia sesión para confirmar tu plan.</p>
            <Button variant="secondary" onClick={resend} loading={busy} loadingLabel="Solicitando enlace…" disabled={cooldown > 0}>
                {cooldown > 0 ? `Reenviar enlace (${cooldown} s)` : 'Reenviar verificación'}
            </Button>
            {resendMessage && <p role="status">{resendMessage}</p>}
            {error && <p ref={errorMessage} tabIndex={-1} role="alert" className={styles.error}>{error}</p>}
            <Link to="/login">Ir a iniciar sesión</Link>
        </div> : <>
            <form onSubmit={submit} noValidate>
                <Input label="Nombre completo" name="name" placeholder="Tu nombre completo" leadingIcon={<UserRound size={18} />} autoComplete="name" maxLength={200} required disabled={busy} error={fieldMessage(errors.name)} />
                <Input label="Correo electrónico" type="email" name="email" placeholder="correo@ejemplo.com" leadingIcon={<Mail size={18} />} autoComplete="email" maxLength={254} required disabled={busy} error={fieldMessage(errors.email)} />
                <PasswordInput label="Contraseña" name="password" placeholder="Crea una contraseña" autoComplete="new-password" minLength={8} maxLength={128}
                    value={password} onChange={updatePassword}
                    hint={<span className={styles.requirements}>
                        <span className={styles.requirements} role="status" aria-live="polite" aria-atomic="true">
                            {requirements.map((requirement) => {
                                const Icon = requirement.met ? Check : Circle;
                                return <span key={requirement.id} className={requirement.met ? styles.valid : undefined}>
                                    <Icon size={14} aria-hidden="true" />
                                    {requirement.label}: {requirement.met ? 'cumplido' : 'pendiente'}
                                </span>;
                            })}
                        </span>
                        <span>Evita contraseñas comunes o parecidas a tus datos. Se comprobarán al crear la cuenta.</span>
                    </span>}
                    required disabled={busy} error={fieldMessage(errors.password)} />
                <PasswordInput label="Confirmar contraseña" visibilityLabel="confirmación de contraseña" name="password_confirmation" placeholder="Repite tu contraseña" autoComplete="new-password" maxLength={128}
                    value={confirmation} onChange={updateConfirmation}
                    hint={!errors.password_confirmation && <span role="status" aria-live="polite" className={confirmation ? (matches ? styles.valid : styles.error) : undefined}>
                        {confirmation ? (matches ? 'Las contraseñas coinciden.' : 'Las contraseñas no coinciden.') : 'Repite la contraseña de arriba.'}
                    </span>}
                    aria-invalid={Boolean(confirmation && !matches)} required disabled={busy} error={fieldMessage(errors.password_confirmation)} />
                {error && <p ref={errorMessage} tabIndex={-1} role="alert" className={styles.error}>{error}</p>}
                <Button type="submit" loading={busy} loadingLabel="Creando cuenta…">Crear cuenta</Button>
            </form>
            <p className={styles.switchPage}>¿Ya tienes cuenta? <Link to="/login">Iniciar sesión</Link></p>
        </>}
    </section>;
}
