import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, XCircle, AlertTriangle, Mail } from 'lucide-react';
import { verificationApi } from '../api/verificationApi';
import styles from './VerifyEmail.module.css';

/**
 * Pantalla M02 - Verificación de Correo (Tarea R3 - Rodrigo)
 *
 * Lee el token de la URL y valida la cuenta.
 * Maneja los estados: verificando, confirmado, inválido, vencido, usado.
 * Permite reenviar el correo en caso de expiración.
 */
export default function VerifyEmail() {
    const [status, setStatus] = useState('pending'); // pending, success, error, resend_prompt
    const [errorCode, setErrorCode] = useState(null); // 'invalid_token', 'expired_token', 'used_token'
    const [emailForResend, setEmailForResend] = useState('');
    const [isResending, setIsResending] = useState(false);
    const [resendMessage, setResendMessage] = useState(null);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');

        if (!token) {
            setStatus('error');
            setErrorCode('invalid_token');
            return;
        }

        const verify = async () => {
            try {
                await verificationApi.verifyEmail(token);
                setStatus('success');
            } catch (err) {
                // El backend de Fase 3 devuelve: { code: 'expired_token', detail: '...' }
                const code = err.code || 'invalid_token';
                setErrorCode(code);
                
                if (code === 'expired_token') {
                    setStatus('resend_prompt');
                } else {
                    setStatus('error');
                }
            }
        };

        verify();
    }, []);

    const handleResend = async (e) => {
        e.preventDefault();
        if (!emailForResend) return;

        setIsResending(true);
        setResendMessage(null);
        try {
            await verificationApi.resendVerification(emailForResend);
            setResendMessage('Si el correo está registrado, se ha enviado un nuevo enlace.');
            setEmailForResend('');
        } catch (err) {
            setResendMessage('Ocurrió un error al intentar reenviar el correo.');
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
                        <a href="/login" className={styles.primaryBtn} style={{ textDecoration: 'none', display: 'block' }}>
                            Ir al inicio de sesión
                        </a>
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
                            <p className={styles.message} style={{ color: '#10b981', fontSize: '0.9rem' }}>
                                {resendMessage}
                            </p>
                        )}

                        <div className={styles.actions}>
                            <button type="submit" className={styles.primaryBtn} disabled={isResending}>
                                {isResending ? (
                                    <><Loader2 size={16} className={styles.spin} style={{ marginRight: '8px', verticalAlign: 'middle' }}/> Enviando...</>
                                ) : (
                                    <><Mail size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Enviar nuevo enlace</>
                                )}
                            </button>
                            <a href="/login" className={styles.secondaryBtn} style={{ textDecoration: 'none', display: 'block', textAlign: 'center' }}>
                                Volver al inicio
                            </a>
                        </div>
                    </form>
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
                        <a href="/login" className={styles.primaryBtn} style={{ textDecoration: 'none', display: 'block' }}>
                            Ir al inicio de sesión
                        </a>
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

