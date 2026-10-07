import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Cloud, HardDrive } from 'lucide-react';
import { useAuth } from '@shared/auth/AuthContext';
import { getAccountIdentity } from '@shared/auth/accountIdentity';
import { getAccountOverview, serviceMessage, validateSubscription } from '@shared/api/accountApi';
import Button from '@shared/components/Button/Button';
import styles from './ProfilePage.module.css';

export default function ProfilePage() {
    const { user } = useAuth();
    const { name, initial, email } = getAccountIdentity(user);
    const [state, setState] = useState({ loading: true, data: null, error: '' });
    const [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let active = true;
        getAccountOverview().then((data) => {
            validateSubscription(data);
            if (data.subscription && (!data.storage || !Number.isFinite(data.storage.used_bytes) ||
                !Number.isFinite(data.storage.capacity_bytes) || data.storage.used_bytes < 0 || data.storage.capacity_bytes <= 0)) {
                throw new Error('No se pudo confirmar el consumo de almacenamiento.');
            }
            if (active) setState({ loading: false, data, error: '' });
        }).catch((failure) => {
            if (active) setState({ loading: false, data: null, error: serviceMessage(failure, 'La consulta de plan y almacenamiento') });
        });
        return () => { active = false; };
    }, [user.id, attempt]);
    const subscription = state.data?.subscription;
    const storage = state.data?.storage;
    const usedPercent = storage ? Math.round(storage.used_bytes / storage.capacity_bytes * 100) : 0;
    const megabytes = (bytes) => (bytes / 1024 / 1024).toLocaleString('es', { maximumFractionDigits: 2 });
    return (
        <section className={styles.page} aria-labelledby="profile-title">
            <header className={styles.heading}>
                <h1 id="profile-title">Mi perfil</h1>
                <p>Consulta la información de tu cuenta.</p>
            </header>
            <section className={styles.card} aria-labelledby="account-info-title">
                <h2 id="account-info-title">Información de la cuenta</h2>
                <div className={styles.identity}>
                    <span className={styles.avatar} aria-hidden="true">{initial}</span>
                    <dl className={styles.fields}>
                        <dt>Nombre visible</dt><dd>{name}</dd>
                        <dt>Correo electrónico</dt><dd>{email || 'No disponible'}</dd>
                    </dl>
                </div>
            </section>
            {state.loading ? <p role="status">Consultando plan y almacenamiento…</p> : state.error ?
                <section className={styles.card}>
                    <p role="alert">{state.error}</p>
                    <Button variant="secondary" onClick={() => { setState({ loading: true, data: null, error: '' }); setAttempt((value) => value + 1); }}>Reintentar</Button>
                </section> : subscription ?
                    <div className={styles.summary}>
                        <section className={styles.card} aria-labelledby="profile-plan-title">
                            <h2 id="profile-plan-title">Plan actual</h2>
                            <div className={styles.plan}>
                                <Cloud size={48} aria-hidden="true" />
                                <div><p className={styles.planName}>{subscription.plan.name}</p><p className={styles.muted}>{megabytes(storage.capacity_bytes)} MB de almacenamiento</p></div>
                            </div>
                        </section>
                        <section className={styles.card} aria-labelledby="profile-storage-title">
                            <h2 id="profile-storage-title"><HardDrive size={20} aria-hidden="true" /> Almacenamiento</h2>
                            <p className={styles.usage}>{megabytes(storage.used_bytes)} MB usados de {megabytes(storage.capacity_bytes)} MB</p>
                            <div className={styles.meter}>
                                <progress max={storage.capacity_bytes} value={Math.min(storage.used_bytes, storage.capacity_bytes)} aria-label="Almacenamiento usado" />
                                <span>{usedPercent} %</span>
                            </div>
                            <p className={styles.muted}>{megabytes(Math.max(0, storage.capacity_bytes - storage.used_bytes))} MB disponibles</p>
                            <p className={styles.note}>La papelera también ocupa espacio.</p>
                        </section>
                    </div> : <section className={styles.card}>
                        <h2>Sin plan activo</h2>
                        <p>Elige y confirma un plan para habilitar tu almacenamiento.</p>
                        <Link to="/plans">Elegir plan</Link>
                    </section>}
            {(state.loading || state.error || subscription) && <Link to="/plans">Consultar planes</Link>}
        </section>
    );
}
