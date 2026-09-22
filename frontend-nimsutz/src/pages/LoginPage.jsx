import { Link } from 'react-router-dom';
import Input from '../shared/components/Input/Input';
import Button from '../shared/components/Button/Button';
import styles from './LoginPage.module.css';

export default function LoginPage() {
    return (
        <section className={styles.page} aria-labelledby="login-title">
            <p>BIENVENIDO A NIM SUTZ’</p>
            <h1 id="login-title">Inicia sesión en tu espacio</h1>
            <p id="login-status">El inicio de sesión aún no está disponible. Vuelve cuando el servicio esté habilitado.</p>
            <form onSubmit={(event) => event.preventDefault()} aria-describedby="login-status">
                <Input label="Correo electrónico" type="email" autoComplete="username" disabled />
                <Input label="Contraseña" type="password" autoComplete="current-password" disabled />
                <Button type="submit" disabled>Iniciar sesión</Button>
            </form>
            <p>¿Aún no tienes cuenta? Registro próximamente.</p>
            <Link to="/">Volver al inicio</Link>
        </section>
    );
}
