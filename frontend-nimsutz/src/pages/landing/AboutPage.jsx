import styles from './Information.module.css';

export default function AboutPage() {
    return (
        <section id="about" className={styles.section} aria-labelledby="about-title" data-reveal="left">
            <p className={styles.eyebrow}>SOBRE NOSOTROS</p>
            <h2 id="about-title" className={styles.aboutTitle}>Un lugar para lo que estás creando.</h2>
            <p className={styles.aboutLead}>Nim sutz’ nace de una idea sencilla: organizar tus documentos
                debería ayudarte a avanzar, no quitarte tiempo.</p>
            <div className={styles.aboutBlock}>
                <h3>Nuestro propósito</h3>
                <p>Reunir archivos y carpetas en un espacio claro y accesible.
                    Queremos que puedas encontrar tus documentos y continuar con tus proyectos
                    sin perderte entre versiones y ubicaciones distintas.</p>
            </div>
            <div className={styles.aboutBlock}>
                <h3>Lo que guía nuestro diseño</h3>
                <div className={styles.values}>
                    <div><h4>Claridad</h4><p>Información comprensible y acciones fáciles de identificar.</p></div>
                    <div><h4>Orden</h4><p>Carpetas y documentos con un lugar propio para cada proyecto.</p></div>
                    <div><h4>Sencillez</h4><p>Dar prioridad a lo que necesitas para trabajar con tus archivos.</p></div>
                </div>
            </div>
        </section>
    );
}