export function formatStorage(bytes) {
    const mb = bytes / 1024 / 1024;
    return mb >= 1024 ? `${Math.round(mb / 1024)} GB` : `${Math.round(mb)} MB`;
}

export const formatPrice = (price) => Number(price);