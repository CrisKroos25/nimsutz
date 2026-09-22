import PlansSection from './landing/PlansSection';
import FaqSection from './landing/FaqSection';
import { CloudUpload, FolderOpen, Download, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import useLandingMotion from './landing/useLandingMotion';
import styles from './LandingPage.module.css';

const FEATURES = [
    {
        icon: CloudUpload,
        title: 'Carga tus archivos',
        text: 'Un espacio para tus documentos, con información clara sobre cada carga.',
    },
    {
        icon: FolderOpen,
        title: 'Organiza a tu manera',
        text: 'Agrupa documentos en carpetas para encontrar lo que necesitas.',
    },
    {
        icon: Download,
        title: 'Tenlos a mano',
        text: 'Consulta tus archivos y descarga una copia cuando la necesites.',
    },
];

export default function LandingPage() {
    const root = useLandingMotion();
    return (
        <div ref={root} className={styles.landing}>
            <section className={styles.hero} aria-labelledby="landing-title">
                <div className={styles.copy}>
                    <p className={styles.eyebrow}>TU ESPACIO EN LA NUBE</p>
                    <h1 id="landing-title">
                        Tus documentos.
                        <br />
                        <span>Un solo lugar.</span>
                    </h1>
                    <p className={styles.lead}>
                        Nim sutz’ reúne tus archivos en un espacio sencillo para
                        cargarlos, organizarlos y volver a encontrarlos.
                    </p>
                    <div className={styles.actions}>
                        <Link to="/login" className={styles.primary}>
                            Iniciar sesión{' '}
                            <ArrowRight size={18} aria-hidden="true" />
                        </Link>
                        <a href="#features" className={styles.secondary}>
                            Descubrir beneficios
                        </a>
                    </div>
                    
                </div>
                <div className={styles.illustration} aria-hidden="true">
                    <div className={styles.cloud}>
                        <CloudUpload size={64} strokeWidth={1.4} />
                    </div>
                    <div className={styles.folder}>
                        <FolderOpen size={32} />
                        <span>Un lugar para tus ideas.</span>
                    </div>
                    <div className={styles.file}>
                        Informes · Proyectos · Documentos
                    </div>
                </div>
            </section>
            <section
                id="features"
                className={styles.features}
                aria-labelledby="features-title"
            >
                <h2 id="features-title">Lo esencial para tus archivos</h2>
                <p className={styles.lead}>
                    De la primera idea a la última versión. Lo esencial, sin complicaciones.
                </p>
                <div className={styles.grid}>
                    {FEATURES.map(({ icon: Icon, title, text }, index) => (
                        <article className={styles.card} key={title}
                            data-reveal={index % 2 ? 'right' : 'left'}>
                            <div className={styles.featureVisual} aria-hidden="true">
                                <span>0{index + 1}</span><Icon size={88} strokeWidth={1} />
                            </div>
                            <div className={styles.featureCopy}>
                            <h3>{title}</h3>
                            <p>{text}</p>
                            </div>
                        </article>
                    ))}
                </div>
            </section>
            <PlansSection />
            <FaqSection />
            <section className={styles.closing} data-reveal="left">
                <p className={styles.eyebrow}>NIM SUTZ’</p>
                <h2>Tu próximo proyecto empieza con una idea.</h2>
                <Link to="/login" className={styles.primary}>Accede a tu espacio <ArrowRight size={18} /></Link>
                <p className={styles.note}>Tus documentos, a un inicio de sesión de distancia.</p>
            </section>
        </div>
    );
}
