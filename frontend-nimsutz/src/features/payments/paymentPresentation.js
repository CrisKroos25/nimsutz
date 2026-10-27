export function formatCardNumber(value) {
    return value.replace(/\D/g, '').slice(0, 16).replace(/(.{4})(?=.)/g, '$1 ');
}

export function formatExpiry(value) {
    const digits = value.replace(/\D/g, '').slice(0, 4);
    return digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
}

export function checkoutCard(form) {
    const [month, year] = String(form.get('expiry')).split('/');
    return {
        number: String(form.get('number')).replace(/\s/g, ''),
        holder: form.get('holder'),
        expiry_month: Number(month),
        expiry_year: 2000 + Number(year),
        security_code: form.get('security_code'),
    };
}

export function paymentAmount(amount, currency) {
    return currency === 'GTQ' ? `Q${amount}` : `${amount} ${currency}`;
}

const calendarDate = (value, year = true) => new Date(value).toLocaleDateString('es-GT', {
    timeZone: 'America/Guatemala', day: 'numeric', month: 'short', ...(year ? { year: 'numeric' } : {}),
});

export function paymentPeriod(startsAt, endsAt) {
    if (!startsAt) return 'Se confirma al completar el pago';
    if (!endsAt) return `Desde ${calendarDate(startsAt)}`;
    const localYear = value => new Date(value).toLocaleDateString('en', { timeZone: 'America/Guatemala', year: 'numeric' });
    return `${calendarDate(startsAt, localYear(startsAt) !== localYear(endsAt))} – ${calendarDate(endsAt)}`;
}
