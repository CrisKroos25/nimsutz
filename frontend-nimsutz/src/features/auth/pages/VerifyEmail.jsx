import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, CheckCircle, XCircle, AlertTriangle, Mail } from 'lucide-react';
import { verificationApi } from '../api/verificationApi';
import styles from './VerifyEmail.module.css';

/**
 * Pantalla M02 - Verificación de Correo (Tarea R3 - Rodrigo)
 *
 * Lee el token de la URL y valida la cuenta.
 * Maneja los estados: verificando, confirmado, inválido, vencido, usado, error de red.
 * Permite reenviar el correo en caso de expiración o reintentar ante fallos de conexión.
 */

const RESEND_COOLDOWN_SECONDS = 60; // debe coincidir con RESEND_COOLDOWN_SECONDS del backend

export default function VerifyEmail() {
    const [status, setStatus] = useState('pending'); // pending, success, error, resend_prompt, network_error
    const [errorCode, setErrorCode] = useState(null); // 'invalid_token', 'expired_token', 'used_token'
    const [emailForResend, setEmailForResend] = useState('');
    const [isResending, setIsResending] = useState(false);
    const [resendMessage, setResendMessage] = useState(null);
    const verificationStarted = useRef(false);
    const [resendError, setResendError] = useState(null);
    const [cooldown, setCooldown] = useState(0);

    const verifyToken = async (targetToken) => {
        if (!targetToken) {
            setStatus('error');
            setErrorCode('invalid_token');
            return;
        }

        setStatus('pending');
        setErrorCode(null);

        try {
            await verificationApi.verifyEmail(targetToken);
            setStatus('success');
        } catch (err) {
            // Distinguir fallos de conexión a internet o caída del servidor (5xx / network offline)
            const isConnectionOrServerError = !err.status || err.status >= 500;
            if (isConnectionOrServerError) {
                setStatus('network_error');
                return;
            }

            const code = err.code || 'invalid_token';
            setErrorCode(code);
            
            if (code === 'expired_token') {
                setStatus('resend_prompt');
            } else {
                setStatus('error');
            }
        }
    };

    useEffect(() => {
        // Evitar doble ejecución concurrente bajo React.StrictMode
        if (verificationStarted.current) return;
        verificationStarted.current = true;

        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        verifyToken(token);
    }, []);

    useEffect(() => {
        if (cooldown <= 0) return undefined;
        const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
        return () => clearTimeout(timer);
    }, [cooldown]);

    const handleResend = async (e) => {
        e.preventDefault();
        const address = emailForResend.trim();
        if (!address || cooldown > 0) return;

        setIsResending(true);
        setResendMessage(null);
        setResendError(null);
        try {
            await verificationApi.resendVerification(address);
            setResendMessage('Si el correo está registrado, se ha enviado un nuevo enlace.');
            setEmailForResend('');
            setCooldown(RESEND_COOLDOWN_SECONDS);
        } catch (failure) {
            if (failure.code === 'resend_cooldown') {
                setCooldown(failure.retryAfter || RESEND_COOLDOWN_SECONDS);
                setResendError('Ya enviamos un enlace hace un momento. Espera para solicitar otro.');
            } else if (failure.code === 'email_delivery_failed') {
                setCooldown(RESEND_COOLDOWN_SECONDS);
                setResendError('No pudimos enviar el correo. Inténtalo de nuevo en un momento.');
            } else {
                setResendError('Ocurrió un error al intentar reenviar el correo.');
            }
        } finally {
            setIsResending(false);
        }
    };

    // ─── RENDERIZADO CONDICIONAL POR ESTADO ────────────────────────────────────

    if (status === 'pending') {
        return (
            <div className={styles.container}>
                <div className={styles.card}>
                    <div className={styles.icon}>
                        <Loader2 size={48} className={styles.spin} />
                    </div>
                    <h1 className={styles.title}>Verificando tu cuenta</h1>
                    <p className={styles.message}>
                        Por favor espera un momento mientras confirmamos tu identidad...
                    </p>
                </div>
            </div>
        );
    }

    if (status === 'success') {
        return (
            <div className={styles.container}>
                <div className={styles.card}>
                    <div className={`${styles.icon} ${styles.success}`}>
                        <CheckCircle size={48} />
                    </div>
                    <h1 className={styles.title}>¡Cuenta verificada!</h1>
                    <p className={styles.message}>
                        Tu dirección de correo ha sido confirmada exitosamente. 
                        Ya puedes iniciar sesión para configurar tu plan de almacenamiento.
                    </p>
                    <div className={styles.actions}>
                        <Link to="/login" className={styles.primaryBtn} style={{ textDecoration: 'none', display: 'block' }}>
                            Ir al inicio de sesión
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    if (status === 'resend_prompt') {
        return (
            <div className={styles.container}>
                <div className={styles.card}>
                    <div className={`${styles.icon} ${styles.error}`}>
                        <AlertTriangle size={48} />
                    </div>
                    <h1 className={styles.title}>El enlace expiró</h1>
                    <p className={styles.message}>
                        Por seguridad, los enlaces de verificación expiran después de 24 horas.
                        Ingresa tu correo para recibir uno nuevo.
                    </p>

                    <form onSubmit={handleResend}>
                        <div className={styles.inputGroup}>
                            <label htmlFor="email">Correo electrónico</label>
                            <input
                                id="email"
                                type="email"
                                required
                                className={styles.input}
                                value={emailForResend}
                                onChange={(e) => setEmailForResend(e.target.value)}
                                placeholder="tu@correo.com"
                                disabled={isResending}
                            />
                        </div>

                        {resendMessage && (
                            <p role="status" className={styles.message} style={{ color: '#10b981', fontSize: '0.9rem' }}>
                                {resendMessage}
                            </p>
                        )}
                        {resendError && (
                            <p role="alert" className={styles.message} style={{ color: '#ef4444', fontSize: '0.9rem' }}>
                                {resendError}
                            </p>
                        )}

                        <div className={styles.actions}>
                            <button type="submit" className={styles.primaryBtn} disabled={isResending || cooldown > 0}>
                                {isResending ? (
                                    <><Loader2 size={16} className={styles.spin} style={{ marginRight: '8px', verticalAlign: 'middle' }}/> Enviando...</>
                                ) : cooldown > 0 ? (
                                    `Reenviar en ${cooldown} s`
                                ) : (
                                    <><Mail size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Enviar nuevo enlace</>
                                )}
                            </button>
                            <Link to="/login" className={styles.secondaryBtn} style={{ textDecoration: 'none', display: 'block', textAlign: 'center' }}>
                                Volver al inicio
                            </Link>
                        </div>
                    </form>
                </div>
            </div>
        );
    }

    if (status === 'network_error') {
        return (
            <div className={styles.container}>
                <div className={styles.card}>
                    <div className={`${styles.icon} ${styles.warning}`}>
                        <AlertTriangle size={48} />
                    </div>
                    <h1 className={styles.title}>Error de conexión</h1>
                    <p className={styles.message}>
                        No pudimos establecer conexión con el servidor para verificar tu cuenta. 
                        Comprueba tu conexión a internet o intenta de nuevo.
                    </p>
                    <div className={styles.actions}>
                        <button 
                            type="button" 
                            className={styles.primaryBtn}
                            onClick={() => {
                                const params = new URLSearchParams(window.location.search);
                                const token = params.get('token');
                                verifyToken(token);
                            }}
                        >
                            Reintentar comprobación
                        </button>
                        <Link to="/login" className={styles.secondaryBtn} style={{ textDecoration: 'none', display: 'block', textAlign: 'center' }}>
                            Ir al inicio de sesión
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    // status === 'error'
    return (
        <div className={styles.container}>
            <div className={styles.card}>
                <div className={`${styles.icon} ${styles.error}`}>
                    <XCircle size={48} />
                </div>
                <h1 className={styles.title}>Enlace inválido</h1>
                <p className={styles.message}>
                    {errorCode === 'used_token' 
                        ? 'Esta cuenta ya ha sido verificada anteriormente. Intenta iniciar sesión.' 
                        : 'El enlace de verificación no es válido o está malformado. Asegúrate de copiarlo completo.'}
                </p>
                <div className={styles.actions}>
                    {errorCode === 'used_token' ? (
                        <Link to="/login" className={styles.primaryBtn} style={{ textDecoration: 'none', display: 'block' }}>
                            Ir al inicio de sesión
                        </Link>
                    ) : (
                        <button 
                            type="button" 
                            className={styles.secondaryBtn}
                            onClick={() => setStatus('resend_prompt')}
                        >
                            Solicitar nuevo enlace
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

