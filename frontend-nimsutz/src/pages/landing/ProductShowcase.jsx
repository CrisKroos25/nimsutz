import { useOutletContext } from 'react-router-dom';
import explorerDark from '../../assets/product/explorer-dark.jpg';
import explorerLight from '../../assets/product/explorer-light.jpg';
import trashDark from '../../assets/product/trash-dark.jpg';
import trashLight from '../../assets/product/trash-light.jpg';
import useProductMotion from './useProductMotion';
import styles from './ProductShowcase.module.css';

export default function ProductShowcase() {
    const root = useProductMotion();
    const { theme } = useOutletContext();
    const isDark = theme === 'dark';
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
                            src={isDark ? explorerDark : explorerLight}
                            alt="Explorador de carpetas de Nim sutz"
                            width="1202"
                            height="668"
                            loading="lazy"
                            decoding="async"
                        />
                    </figure>
                    <figure className={styles.trash}>
                        <img
                            src={isDark ? trashDark : trashLight}
                            alt="Papelera de Nim sutz"
                            width="1202"
                            height="668"
                            loading="lazy"
                            decoding="async"
                        />
                    </figure>
                </div>
            </div>
        </section>
    );
}
