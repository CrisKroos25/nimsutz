import { Link } from 'react-router-dom';
import styles from './AboutPage.module.css';

export default function AboutPage() {
    return (
        <article className={styles.page}>
            <p className={styles.eyebrow}>SOBRE NOSOTROS</p>
            <h1>Un lugar para lo que estás creando.</h1>
            <p className={styles.lead}>Nim sutz’ nace de una idea sencilla: organizar tus documentos
                debería ayudarte a avanzar, no quitarte tiempo.</p>
            <section>
                <h2>Nuestro propósito</h2>
                <p>Reunir archivos y carpetas en un espacio claro y accesible.
                    Queremos que puedas encontrar tus documentos y continuar con tus proyectos
                    sin perderte entre versiones y ubicaciones distintas.</p>
            </section>
            <section>
                <h2>Lo que guía nuestro diseño</h2>
                <div className={styles.values}>
                    <div><h3>Claridad</h3><p>Información comprensible y acciones fáciles de identificar.</p></div>
                    <div><h3>Orden</h3><p>Carpetas y documentos con un lugar propio para cada proyecto.</p></div>
                    <div><h3>Sencillez</h3><p>Dar prioridad a lo que necesitas para trabajar con tus archivos.</p></div>
                </div>
            </section>
            <Link to="/">Volver a Nim sutz’</Link>
        </article>
    );
}
