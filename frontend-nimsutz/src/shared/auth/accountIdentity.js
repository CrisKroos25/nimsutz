const ROLE_LABELS = {
    administrador: 'Administrador',
};

export function getAccountIdentity(user) {
    const email = user?.email?.trim() || '';
    const name = user?.name?.trim() || email.split('@')[0] || 'Mi cuenta';
    const initial = Array.from(name)[0]?.toLocaleUpperCase() ?? '?';
    const roleLabel = ROLE_LABELS[user?.role] ?? null;

    return { email, name, initial, roleLabel };
}