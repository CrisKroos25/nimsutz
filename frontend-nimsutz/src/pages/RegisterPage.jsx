import { useEffect, useRef, useState } from 'react';
import { Check, Circle, CloudUpload, Download, FolderOpen, Mail } from 'lucide-react';
import PasswordInput from '@shared/components/Input/PasswordInput';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '@shared/auth/AuthContext';
import { fieldMessage, readPlanPreference, validateRegistration, passwordRequirements } from '@shared/auth/accessFlow';
import { registerAccount, serviceMessage } from '@shared/api/accountApi';
import Input from '@shared/components/Input/Input';
import Button from '@shared/components/Button/Button';
import { verificationApi } from '@features/auth/api/verificationApi';
import styles from './LoginPage.module.css';
import layout from './RegisterPage.module.css';
import Brand from '@layouts/Brand';
import logo from "../assets/nube.png";
import SessionLoader from '@shared/auth/SessionLoader';

const HIGHLIGHTS = [
    { icon: CloudUpload, title: 'Carga tus archivos', text: 'Un espacio para tus documentos, con información clara sobre cada carga.' },
    { icon: FolderOpen, title: 'Organiza a tu manera', text: 'Agrupa documentos en carpetas para encontrar lo que necesitas.' },
    { icon: Download, title: 'Tenlos a mano', text: 'Consulta tus archivos y descarga una copia cuando la necesites.' },
];
const RESEND_COOLDOWN_SECONDS = 60; // debe coincidir con RESEND_COOLDOWN_SECONDS del backend

export default function RegisterPage() {
    const { user, loading, destination, error: sessionError } = useAuth();
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

    useEffect(() => { window.scrollTo(0, 0); }, []);
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
            setCooldown(RESEND_COOLDOWN_SECONDS);
        } catch (failure) {
            if (failure.code === 'resend_cooldown') {
                // Demasiado pronto: se muestra la cuenta regresiva que indica el servidor.
                setCooldown(failure.retryAfter || RESEND_COOLDOWN_SECONDS);
            } else if (failure.code === 'email_delivery_failed') {
                // El servidor ya consumió la espera de este intento.
                setCooldown(RESEND_COOLDOWN_SECONDS);
                setError(failure.message);
            } else {
                setError(serviceMessage(failure, 'El reenvío de verificación'));
            }
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
            setCooldown(RESEND_COOLDOWN_SECONDS);
            setPassword('');
            setConfirmation('');
            form.reset();
        } catch (failure) {
            if (failure.code === 'email_delivery_failed') {
                // La cuenta quedó creada y pendiente: se pasa a la pantalla de verificación para reenviar.
                setRegistered({ email: values.email.trim(), emailSent: false });
                setCooldown(RESEND_COOLDOWN_SECONDS);
                setPassword('');
                setConfirmation('');
                form.reset();
            } else {
                setErrors(failure.fieldErrors || {});
                setError(serviceMessage(failure, 'El registro'));
            }
        } finally { submitting.current = false; setBusy(false); }
    }

    if (loading) return <SessionLoader fullScreen />;
    if (user) return <Navigate to={destination} replace />;
    return <div className={layout.shell}>
        <aside className={layout.aside}>
            <img src={logo} alt="Logo de Nim Sutz" className={layout.logo} />
            <div className={layout.asideContent}>
                <Brand />
                <h2>Tus documentos<br /><span>en un solo lugar.</span></h2>
                <p className={layout.asideLead}>Crea tu cuenta gratis y empieza a cargar, organizar y volver a encontrar tus archivos.</p>
                <ul className={layout.highlights}>
                    {HIGHLIGHTS.map(({ icon: Icon, title, text }) => <li key={title}>
                        <span className={layout.highlightIcon} aria-hidden="true"><Icon size={16} /></span>
                        <span><strong>{title}</strong><span>{text}</span></span>
                    </li>)}
                </ul>
            </div>
        </aside>

        <main className={layout.main} id="main-content">
            <div className={layout.topbar}>
                <span className={layout.signin}>¿Ya tienes cuenta? <Link to="/login">Iniciar sesión</Link></span>
            </div>

            <section className={layout.content} aria-labelledby="register-title">
                <p className={layout.mobileBrand}>NIM SUTZ’</p>
                <header className={layout.heading}>
                    {registered && <span className={layout.verifyIcon} aria-hidden="true"><Mail size={24} /></span>}
                    <h1 id="register-title" ref={registered ? resultHeading : null} tabIndex={registered ? -1 : undefined}>
                        {registered ? 'Revisa tu correo' : 'Crear cuenta'}
                    </h1>
                    {!registered && <p>Tu espacio para organizar y guardar documentos.</p>}
                </header>

                {registered ? <div className={layout.verify}>
                    <span className={layout.pending}>Verificación pendiente</span>
                    <p className={layout.verifyText} role="status">
                        {registered.emailSent
                            ? <>Enviamos un enlace a <strong>{registered.email}</strong>. Ábrelo para verificar tu cuenta.</>
                            : <>La cuenta <strong>{registered.email}</strong> está creada, pero no pudimos enviar el correo de verificación. Podrás reenviarlo en unos segundos.</>}
                    </p>
                    <p className={layout.verifyNote}>Después de verificar, inicia sesión para confirmar tu plan.</p>
                    <div className={layout.verifyActions}>
                        <Button variant="secondary" onClick={resend} loading={busy} loadingLabel="Solicitando enlace…" disabled={cooldown > 0}>
                            {cooldown > 0 ? `Reenviar enlace (${cooldown} s)` : 'Reenviar verificación'}
                        </Button>
                        {resendMessage && <p role="status" className={layout.resendOk}>{resendMessage}</p>}
                        {error && <p ref={errorMessage} tabIndex={-1} role="alert" className={styles.error}>{error}</p>}
                        <Link to="/login" className={layout.verifyLink}>Ir a iniciar sesión</Link>
                    </div>
                </div> : <>
                    {sessionError && <p role="status" className={layout.error}>
                        No pudimos conectar con el servicio. Si el registro falla, inténtalo de nuevo en unos minutos.
                    </p>}
                    <form className={layout.form} onSubmit={submit} noValidate>
                        <Input label="Nombre completo" name="name" placeholder="Tu nombre completo" autoComplete="name" maxLength={200} required disabled={busy} error={fieldMessage(errors.name)} />
                        <Input label="Correo electrónico" type="email" name="email" placeholder="correo@ejemplo.com" autoComplete="email" maxLength={254} required disabled={busy} error={fieldMessage(errors.email)} />
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
                </>}
            </section>
        </main>
    </div>;
}