import explorer from '../../assets/product/explorer-dark.png';
import trash from '../../assets/product/trash-dark.png';
import useProductMotion from './useProductMotion';
import styles from './ProductShowcase.module.css';

export default function ProductShowcase() {
    const root = useProductMotion();
    return (
        <section
            ref={root}
            className={styles.showcase}
            data-product-showcase
            aria-labelledby="product-showcase-title"
        >
            <div className={styles.inner}>
                <h2 id="product-showcase-title" className={styles.title}>
                    Así se ve tu espacio en Nim sutz’.
                </h2>
                <div className={styles.stage}>
                    <figure className={styles.explorer}>
                        <img
                            src={explorer}
                            alt="Explorador de Nim sutz’ en modo oscuro con carpetas, archivos y panel de detalles"
                            width="1000"
                            height="448"
                            loading="lazy"
                            decoding="async"
                        />
                    </figure>
                    <figure className={styles.trash}>
                        <img
                            src={trash}
                            alt="Papelera de Nim sutz’ en modo oscuro"
                            width="1000"
                            height="454"
                            loading="lazy"
                            decoding="async"
                        />
                    </figure>
                </div>
            </div>
        </section>
    );
}
