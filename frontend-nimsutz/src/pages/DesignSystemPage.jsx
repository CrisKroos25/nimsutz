import { useState } from 'react';
import FormExamples from './examples/FormExamples';
import Button from '../shared/components/Button/Button';
import TableExamples from './examples/TableExamples';
import styles from './DesignSystemPage.module.css';

const GROUPS = [
    {
        variant: 'primary',
        title: 'Primario',
        labels: ['Cargar archivo', 'Iniciar sesión'],
    },
    {
        variant: 'secondary',
        title: 'Secundario',
        labels: ['Nueva carpeta', 'Ver detalles'],
    },
    {
        variant: 'danger',
        title: 'Peligro',
        labels: ['Eliminar carpeta', 'Revocar acceso'],
    },
    {
        variant: 'ghost',
        title: 'Sin fondo · Ghost',
        labels: ['Cancelar', 'Volver'],
    },
];

export default function DesignSystemPage() {
    const [message, setMessage] = useState(
        'Selecciona un botón para probarlo.',
    );
    const [loading, setLoading] = useState(false);

    return (
        <div className={styles.page}>
            <div className={styles.main}>
                <section className={styles.intro} aria-labelledby="page-title">
                    <p className={styles.eyebrow}>SISTEMA DE DISEÑO</p>
                    <h1 id="page-title">
                        Nim sutz’ — Identidad visual atardecer
                    </h1>
                    <p className={styles.muted}>
                        Tipografía y botones compartidos. Explora sus estados en
                        los temas claro y oscuro.
                    </p>
                </section>
                <section aria-labelledby="type-title">
                    <h2 id="type-title" className={styles.sectionTitle}>
                        Tipografía — Poppins
                    </h2>
                    <div className={styles.panel}>
                        <p className={styles.headingExample}>
                            Gestión documental inteligente
                        </p>
                        <h2>Carpetas y archivos recientes</h2>
                        <p>
                            Nim sutz’ centraliza tus documentos en un solo
                            lugar.
                        </p>
                        <p className={styles.small}>
                            Texto pequeño · 14 px · Regular
                        </p>
                    </div>
                </section>
                <section aria-labelledby="buttons-title">
                    <h2 id="buttons-title" className={styles.sectionTitle}>
                        Botones
                    </h2>
                    <div className={styles.panel}>
                        {GROUPS.map(({ variant, title, labels }) => (
                            <div className={styles.group} key={variant}>
                                <h3>{title}</h3>
                                <div className={styles.row}>
                                    {labels.map((label) => (
                                        <Button
                                            key={label}
                                            variant={variant}
                                            onClick={() =>
                                                setMessage(
                                                    `Probaste «${label}». Es una demostración.`,
                                                )
                                            }
                                        >
                                            {label}
                                        </Button>
                                    ))}
                                    <Button variant={variant} disabled>
                                        Desactivado
                                    </Button>
                                </div>
                            </div>
                        ))}
                        <p className={styles.feedback} role="status">
                            {message}
                        </p>
                    </div>
                </section>
                <section aria-labelledby="loading-title">
                    <h2 id="loading-title" className={styles.sectionTitle}>
                        Estado de carga
                    </h2>
                    <div className={styles.panel}>
                        <p className={styles.muted}>
                            Mientras una acción está en curso, el botón impide
                            nuevos clics.
                        </p>
                        <div className={styles.row}>
                            <Button
                                loading={loading}
                                loadingLabel="Guardando…"
                                onClick={() => setLoading(true)}
                            >
                                Probar carga
                            </Button>
                            <Button
                                variant="ghost"
                                disabled={!loading}
                                onClick={() => setLoading(false)}
                            >
                                Restablecer ejemplo
                            </Button>
                        </div>
                        <p role="status">
                            {loading
                                ? 'Demostración de carga activa.'
                                : 'Listo para probar.'}
                        </p>
                    </div>
                </section>
                <FormExamples />
                <TableExamples />
            </div>
            <footer className={styles.footer}>
                Nim sutz’ · Componentes compartidos
            </footer>
        </div>
    );
}
