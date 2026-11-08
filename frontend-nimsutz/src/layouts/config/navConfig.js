import { Folder, Receipt, Trash2, Wallet, ListTree, Layers, LayoutDashboard, CreditCard, ScrollText, Users } from 'lucide-react';

export const CLIENT_NAV = {
    files: { to: '/files', label: 'Mis archivos', icon: Folder },
    plans: { to: '/plans', label: 'Planes', icon: ListTree },
    subscription: { to: '/subscription', label: 'Mi suscripción', icon: Wallet },
    payments: { to: '/payments/history', label: 'Pagos', icon: Receipt },
    trash: { to: '/trash', label: 'Papelera', icon: Trash2 },
};

export const ADMIN_NAV = [
    { to: '/administration', label: 'Panel', icon: LayoutDashboard, end: true },
    { to: '/administration/clients', label: 'Clientes', icon: Users },
    { to: '/administration/payments', label: 'Pagos', icon: CreditCard },
    { to: '/administration/plans', label: 'Planes', icon: Layers },
    { to: '/administration/audit', label: 'Auditoría', icon: ScrollText },
];