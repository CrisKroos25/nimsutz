import Sidebar from '../Sidebar';
import { ADMIN_NAV } from './navConfig';

export function AdminSidebar(props) {
    return <Sidebar {...props} items={ADMIN_NAV} />;
}