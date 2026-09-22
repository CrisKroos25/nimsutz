import { Check } from 'lucide-react';
import Button from '../../shared/components/Button/Button';
import styles from './Information.module.css';

const PLANS = [
    { name: 'Gratis', price: 0, storage: '100 MB' },
    { name: 'Básico', price: 15, storage: '1 GB' },
    { name: 'Premium', price: 30, storage: '5 GB' },
];

const FEATURES = [
    'Cargar archivos',
    'Descargar tus documentos',
    'Organizar en carpetas',
    'Renombrar y mover archivos',
];

export default function PlansSection() {
    return (
        <section
            id="plans"
            className={styles.section}
            aria-labelledby="plans-title"
            data-reveal="left"
        >
            <p className={styles.eyebrow}>UN ESPACIO A TU MEDIDA</p>
            <h2 id="plans-title">Elige el espacio para tus ideas</h2>
            <p>Tus documentos, organizados. Encuentra el plan que va contigo.</p>
            <div className={styles.plans}>
                {PLANS.map((plan) => (
                    <article className={styles.plan} key={plan.name}>
                        <div className={styles.planHeading}>
                            <h3>{plan.name}</h3>
                            <p className={styles.price}>
                                <span className={styles.currency}>Q</span>
                                <strong>{plan.price}</strong>
                                {plan.price > 0 && <span className={styles.period}>/ mes</span>}
                            </p>
                            <p className={styles.storage}>
                                <strong>{plan.storage}</strong> de almacenamiento
                            </p>
                        </div>
                        <ul className={styles.featureList}>
                            {FEATURES.map((feature) => (
                                <li key={feature}>
                                    <Check size={18} aria-hidden="true" />
                                    <span>{feature}</span>
                                </li>
                            ))}
                        </ul>
                        <Button disabled className={styles.planAction}>
                            Próximamente
                        </Button>
                    </article>
                ))}
            </div>
        </section>
    );
}
