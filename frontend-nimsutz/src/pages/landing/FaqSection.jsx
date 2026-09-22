import styles from './Information.module.css';

export default function FaqSection() {
    return (
        <section id="questions" className={styles.section} aria-labelledby="questions-title" data-reveal="right">
            <p className={styles.eyebrow}>ANTES DE EMPEZAR</p>
            <h2 id="questions-title">Preguntas frecuentes</h2>
            <details><summary>¿Qué puedo hacer con Nim sutz’?</summary><p>Reunir tus documentos en un espacio en la nube, organizarlos en carpetas y descargar una copia cuando la necesites.</p></details>
            <details><summary>¿Necesito una cuenta para ver mis archivos?</summary><p>Sí. El acceso a tus archivos requiere iniciar sesión. La información de esta página es pública.</p></details>
            <details><summary>¿Puedo registrarme ahora?</summary><p>El registro todavía no está disponible. La apertura de nuevas cuentas se anunciará aquí.</p></details>
            <details><summary>¿Dónde consulto precios y capacidades?</summary><p>En la sección de planes puedes comparar precios y almacenamiento. La contratación todavía no está disponible.</p></details>
        </section>
    );
}
