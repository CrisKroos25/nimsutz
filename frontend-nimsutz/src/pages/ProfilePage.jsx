import { Cloud, HardDrive } from 'lucide-react';
import { useAuth } from '@shared/auth/AuthContext';
import { getAccountIdentity } from '@shared/auth/accountIdentity';
import styles from './ProfilePage.module.css';

// Solo presentación: no modifica la cuota real ni representa una suscripción.
const DEMO_PLAN = { name: 'Básico', capacityMB: 1000, usedMB: 250 };

export default function ProfilePage() {
    const { user } = useAuth();
    const { name, initial, email } = getAccountIdentity(user);
    const availableMB = DEMO_PLAN.capacityMB - DEMO_PLAN.usedMB;
    const usedPercent = Math.round(DEMO_PLAN.usedMB / DEMO_PLAN.capacityMB * 100);

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
            <p className={styles.demo}>Plan y almacenamiento de demostración. No representan tu consumo real.</p>
            <div className={styles.summary}>
                <section className={styles.card} aria-labelledby="profile-plan-title">
                    <h2 id="profile-plan-title">Plan actual</h2>
                    <div className={styles.plan}>
                        <Cloud size={48} aria-hidden="true" />
                        <div><p className={styles.planName}>{DEMO_PLAN.name}</p><p className={styles.muted}>1 GB de almacenamiento</p></div>
                    </div>
                </section>
                <section className={styles.card} aria-labelledby="profile-storage-title">
                    <h2 id="profile-storage-title"><HardDrive size={20} aria-hidden="true" /> Almacenamiento</h2>
                    <p className={styles.usage}>{DEMO_PLAN.usedMB} MB usados de 1 GB</p>
                    <div className={styles.meter}>
                        <progress max={DEMO_PLAN.capacityMB} value={DEMO_PLAN.usedMB} aria-label="Almacenamiento usado de demostración" />
                        <span>{usedPercent} %</span>
                    </div>
                    <p className={styles.muted}>{availableMB} MB disponibles</p>
                    <p className={styles.note}>La papelera también ocupa espacio.</p>
                </section>
            </div>
        </section>
    );
}
