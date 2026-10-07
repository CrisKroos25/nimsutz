export function getAccountIdentity(user) {
    const email = user?.email?.trim() || '';
    const name = email.split('@')[0] || 'Mi cuenta';
    return { email, name, initial: Array.from(name)[0].toLocaleUpperCase() };
}
