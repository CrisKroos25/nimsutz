# Base de integración para el integrante A

## Estado

La base de layouts y rutas está preparada localmente y aún requiere un PR. El catálogo ya tiene un commit independiente. Esta base no implementa llamadas al backend.

## Archivos que recibe A

- src/layouts/MainLayout.jsx, Header.jsx, Sidebar.jsx y Layouts.module.css.
- src/router/AppRouter.jsx y src/App.jsx.
- src/pages/StoragePreviewPage.jsx, una pantalla temporal que debe sustituirse por el explorador real.

Brand.jsx, Brand.module.css y ThemeToggle.jsx son piezas comunes ya iniciadas. PublicLayout tiene su propio CSS para evitar que A y C editen la misma hoja. Mantener estos componentes comunes al integrar el layout.

## Contrato con la landing

C entrega LandingPage como exportación predeterminada y PublicLayout con Outlet. PublicLayout recibe theme y toggleTheme. AppRouter monta useTheme una sola vez y lo pasa a los layouts.

La ruta / muestra LandingPage; /files debe mostrar la página real de A; /design-system conserva el catálogo. A añadirá /trash con la página que entregue B.

La landing enlaza a /files y señala que todavía es una demostración. C actualizará ese texto cuando la integración real esté comprobada.

## Dependencias y entrega

La base necesita react-router-dom además de lucide-react. Incluir el cambio de package.json y del lockfile con la base, conservando el gestor acordado.

No copiar los datos de TableExamples como datos reales. No eliminar cambios locales de la landing al preparar el PR. Probar navegación, tema y ruta desconocida después de sustituir StoragePreviewPage.
