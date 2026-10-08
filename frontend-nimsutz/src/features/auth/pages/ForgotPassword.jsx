import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, MailCheck } from 'lucide-react';
import Input from '@shared/components/Input/Input';
import Button from '@shared/components/Button/Button';
import { fieldMessage } from '@shared/auth/accessFlow';
import { recoveryApi, recoveryMessage } from '../api/recoveryApi';
import LinkButton from '../components/LinkButton';
import styles from './Recovery.module.css';

const RESEND_SECONDS = 30;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Pantalla M04 - Recuperar contraseña.
 *
 * Estados: formulario, enviando, enlace solicitado y error. El servidor responde
 * igual exista o no la cuenta, por eso el texto nunca afirma que el correo existe.
 */
export default function ForgotPassword() {
    const submitting = useRef(false);
    const heading = useRef(null);
    const [email, setEmail] = useState('');
    const [sent, setSent] = useState(false);
    const [busy, setBusy] = useState(false);
    const [fieldError, setFieldError] = useState('');
    const [error, setError] = useState('');
    const [cooldown, setCooldown] = useState(0);

    // Al mostrar la confirmación, el foco pasa al título para lectores de pantalla.
    useEffect(() => {
        if (sent) heading.current?.focus();
    }, [sent]);

    useEffect(() => {
        if (cooldown <= 0) return undefined;
        const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
        return () => clearTimeout(timer);
    }, [cooldown]);

    // Devuelve true si el servidor aceptó la solicitud.
    async function request(address) {
        if (submitting.current) return false;
        submitting.current = true;
        setBusy(true);
        setError('');
        setFieldError('');
        try {
            await recoveryApi.requestReset(address);
            return true;
        } catch (failure) {
            const invalidEmail = fieldMessage(failure.fieldErrors?.email);
            if (invalidEmail) setFieldError(invalidEmail);
            else setError(recoveryMessage(failure));
            return false;
        } finally {
            submitting.current = false;
            setBusy(false);
        }
    }

    async function submit(event) {
        event.preventDefault();
        const address = new FormData(event.currentTarget).get('email').trim();
        if (!EMAIL_PATTERN.test(address)) {
            setFieldError('Ingresa un correo válido.');
            return;
        }
        setEmail(address);
        if (await request(address)) {
            setSent(true);
            setCooldown(RESEND_SECONDS);
        }
    }

    async function resend() {
        if (cooldown > 0) return;
        if (await request(email)) setCooldown(RESEND_SECONDS);
    }

    if (sent) {
        return (
            <section className={styles.page} aria-labelledby="forgot-title">
                <div className={styles.status} role="status">
                    <span className={styles.icon} aria-hidden="true"><MailCheck size={28} /></span>
                    <h1 id="forgot-title" ref={heading} tabIndex={-1}>Revisa tu bandeja de entrada</h1>
                    <p>
                        Si existe una cuenta con <strong>{email}</strong>, te enviamos un enlace para
                        crear una contraseña nueva. El enlace tiene una vigencia limitada y solo
                        funciona una vez. Revisa también la carpeta de spam.
                    </p>
                </div>
                {error && <p role="alert" className={styles.error}>{error}</p>}
                <div className={styles.actions}>
                    <LinkButton to="/login">Ir a iniciar sesión</LinkButton>
                    <Button variant="secondary" onClick={resend} loading={busy} loadingLabel="Enviando enlace…" disabled={cooldown > 0}>
                        {cooldown > 0 ? `Reenviar enlace (${cooldown} s)` : 'Reenviar enlace'}
                    </Button>
                </div>
            </section>
        );
    }

    return (
        <section className={styles.page} aria-labelledby="forgot-title">
            <header className={styles.heading}>
                <h1 id="forgot-title">Recuperar contraseña</h1>
                <p>Ingresa el correo asociado a tu cuenta.</p>
            </header>
            <form onSubmit={submit} noValidate>
                <Input
                    label="Correo electrónico"
                    type="email"
                    name="email"
                    placeholder="usuario@correo.com"
                    leadingIcon={<Mail size={18} />}
                    autoComplete="email"
                    maxLength={254}
                    required
                    disabled={busy}
                    error={fieldError}
                />
                {error && <p role="alert" className={styles.error}>{error}</p>}
                <Button type="submit" loading={busy} loadingLabel="Enviando enlace…">Enviar enlace</Button>
            </form>
            <p className={styles.back}><Link to="/login">Volver a iniciar sesión</Link></p>
        </section>
    );
}
