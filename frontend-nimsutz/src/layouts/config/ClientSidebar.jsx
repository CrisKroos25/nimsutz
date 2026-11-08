import { useHasSubscription } from '@shared/hooks/useHasSubscription';
import Sidebar from '../Sidebar';
import SidebarStorage from '../SidebarStorage';
import { CLIENT_NAV } from './navConfig';

export function ClientSidebar(props) {
    const hasSubscription = useHasSubscription();
    const items = [
        hasSubscription ? CLIENT_NAV.files : CLIENT_NAV.plans,
        CLIENT_NAV.subscription,
        CLIENT_NAV.payments,
        CLIENT_NAV.trash,
    ];
    return <Sidebar {...props} items={items} footer={<SidebarStorage />} />;
}
