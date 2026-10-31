import { getPlans, serviceMessage } from '@shared/api/accountApi';
import { useAsyncResource } from './useAsyncResource';

const EMPTY_PLANS = [];

export function usePlans() {
    const { data: plans, loading, error, reload, replace } = useAsyncResource(getPlans, EMPTY_PLANS);
    return { plans, loading, error: error ? serviceMessage(error, 'La consulta de planes') : '', reload, replace };
}
