import { useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Check, CheckCircle2, Circle, LinkIcon, TriangleAlert } from 'lucide-react';
import PasswordInput from '@shared/components/Input/PasswordInput';
import Button from '@shared/components/Button/Button';
import { fieldMessage, passwordRequirements } from '@shared/auth/accessFlow';
import { recoveryApi, recoveryMessage } from '../api/recoveryApi';
import LinkButton from '../components/LinkButton';
import styles from './Recovery.module.css';

/**
 * Pantalla M05 - Restablecer contraseña.
 *
 * Lee el token de la URL (?token=...). Estados: formulario, guardando,
 * contraseña actualizada y enlace no válido o vencido. Los validadores finales
 * son los del servidor; aquí solo se adelantan las reglas simples.
 */
export default function ResetPassword() {
    const [params] = useSearchParams();
    const token = params.get('token') || '';
    const submitting = useRef(false);
    const [password, setPassword] = useState('');
    const [confirmation, setConfirmation] = useState('');
    const [busy, setBusy] = useState(false);
    const [errors, setErrors] = useState({});
    const [error, setError] = useState('');
    const [status, setStatus] = useState(token ? 'form' : 'invalid');
    const [invalidReason, setInvalidReason] = useState('');
    const requirements = passwordRequirements(password);
    const matches = confirmation.length > 0 && confirmation === password;

    function validate() {
        const found = {};
        if (!requirements[0].met) found.password = 'Usa al menos ocho caracteres.';
        else if (!requirements[1].met) found.password = 'La contraseña no puede contener únicamente números.';
        if (!confirmation) found.confirmation = 'Confirma tu contraseña.';
        else if (confirmation !== password) found.confirmation = 'Las contraseñas no coinciden.';
        return found;
    }

    async function submit(event) {
        event.preventDefault();
        if (submitting.current) return;
        const form = event.currentTarget;
        const found = validate();
        setErrors(found);
        setError('');
        if (Object.keys(found).length) {
            form.elements.namedItem(found.password ? 'new_password' : 'confirmation')?.focus();
            return;
        }
        submitting.current = true;
        setBusy(true);
        try {
            await recoveryApi.confirmReset(token, password);
            setPassword('');
            setConfirmation('');
            setStatus('done');
        } catch (failure) {
            if (failure.status === 401) {
                setInvalidReason(failure.message);
                setStatus('invalid');
            } else {
                const serverMessage = fieldMessage(failure.fieldErrors?.new_password);
                if (serverMessage) setErrors({ password: serverMessage });
                else setError(recoveryMessage(failure));
            }
        } finally {
            submitting.current = false;
            setBusy(false);
        }
    }

    if (status === 'done') {
        return (
            <section className={styles.page} aria-labelledby="reset-title">
                <div className={styles.status} role="status">
                    <span className={`${styles.icon} ${styles.iconSuccess}`} aria-hidden="true"><CheckCircle2 size={28} /></span>
                    <h1 id="reset-title" className={styles.titleSuccess}>Contraseña actualizada</h1>
                    <p>
                        Ya puedes iniciar sesión con tu nueva contraseña. Por seguridad, cerramos
                        las sesiones que tenías abiertas.
                    </p>
                </div>
                <div className={styles.actions}>
                    <LinkButton to="/login">Ir a iniciar sesión</LinkButton>
                </div>
            </section>
        );
    }

    if (status === 'invalid') {
        return (
            <section className={styles.page} aria-labelledby="reset-title">
                <div className={styles.status} role="status">
                    <span className={`${styles.icon} ${styles.iconDanger}`} aria-hidden="true">
                        {token ? <TriangleAlert size={28} /> : <LinkIcon size={28} />}
                    </span>
                    <h1 id="reset-title">Enlace no válido o vencido</h1>
                    <p>
                        {invalidReason || 'El enlace está incompleto o ya no sirve.'} Solicita uno
                        nuevo para continuar.
                    </p>
                </div>
                <div className={styles.actions}>
                    <LinkButton to="/forgot-password">Solicitar nuevo enlace</LinkButton>
                    <LinkButton to="/login" variant="secondary">Ir a iniciar sesión</LinkButton>
                </div>
            </section>
        );
    }

    return (
        <section className={styles.page} aria-labelledby="reset-title">
            <header className={styles.heading}>
                <h1 id="reset-title">Crear contraseña nueva</h1>
                <p>Elige una contraseña segura para tu cuenta.</p>
            </header>
            <form onSubmit={submit} noValidate>
                <PasswordInput
                    label="Contraseña nueva"
                    name="new_password"
                    placeholder="Crea una contraseña"
                    autoComplete="new-password"
                    maxLength={128}
                    value={password}
                    onChange={(event) => {
                        setPassword(event.target.value);
                        setErrors({});
                    }}
                    hint={
                        <span className={styles.requirements} role="status" aria-live="polite" aria-atomic="true">
                            {requirements.map((requirement) => {
                                const Icon = requirement.met ? Check : Circle;
                                return (
                                    <span key={requirement.id} className={requirement.met ? styles.valid : undefined}>
                                        <Icon size={14} aria-hidden="true" />
                                        {requirement.label}: {requirement.met ? 'cumplido' : 'pendiente'}
                                    </span>
                                );
                            })}
                            <span>Evita contraseñas comunes o parecidas a tus datos.</span>
                        </span>
                    }
                    required
                    disabled={busy}
                    error={errors.password}
                />
                <PasswordInput
                    label="Confirmar contraseña"
                    visibilityLabel="confirmación de contraseña"
                    name="confirmation"
                    placeholder="Repite tu contraseña"
                    autoComplete="new-password"
                    maxLength={128}
                    value={confirmation}
                    onChange={(event) => {
                        setConfirmation(event.target.value);
                        setErrors((previous) => ({ ...previous, confirmation: undefined }));
                    }}
                    hint={
                        !errors.confirmation && (
                            <span role="status" aria-live="polite" className={confirmation ? (matches ? styles.valid : styles.error) : undefined}>
                                {confirmation
                                    ? matches ? 'Las contraseñas coinciden.' : 'Las contraseñas no coinciden.'
                                    : 'Repite la contraseña de arriba.'}
                            </span>
                        )
                    }
                    required
                    disabled={busy}
                    error={errors.confirmation}
                />
                {error && <p role="alert" className={styles.error}>{error}</p>}
                <Button type="submit" loading={busy} loadingLabel="Guardando…">Guardar contraseña</Button>
            </form>
        </section>
    );
}
