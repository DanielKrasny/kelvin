import { toastApi } from './toast';

export function csrfToken() {
    return document.querySelector('meta[name=csrf-token]').getAttribute('content');
}

export interface PaginatedResponse<T> {
    items: T[];
    count: number;
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/**
 * Get data from API
 *
 * @param url url to fetch
 * @param data data which will be sent to the API
 * @param method HTTP method, if you want to override the default GET/POST
 * @note If data is passed, the request will be a POST request, otherwise a GET request, if not overridden by method parameter
 * @param headers Headers for the request
 *
 * @returns $ReturnType, if the request was successful, otherwise undefined
 */
export const getFromAPI = async <$ReturnType>(
    url: string,
    method?: Method,
    data?: unknown,
    headers?: HeadersInit,
    showErrorToast = false
): Promise<$ReturnType | undefined> => {
    try {
        const response = await fetch(url, {
            method: method || (data ? 'POST' : 'GET'),
            headers,
            body: data ? JSON.stringify(data) : undefined
        });

        const json = await response.json();
        if (!response.ok) {
            if (json?.detail && showErrorToast) {
                toastApi.error(json.detail);
            }
            return undefined;
        }
        return json as $ReturnType;
    } catch (error) {
        console.error(error);
        return undefined;
    }
};

/**
 * Get data from endpoint with {@link getFromAPI()}, but with already filled header `X-CSRFToken`.
 *
 * @param url url to fetch
 * @param data data which will be sent to the API
 * @param method HTTP method, if you want to override the default GET/POST
 * @param showErrorToast Whether to show an error toast on failure
 * @note If data is passed, the request will be a POST request, otherwise a GET request, if not overridden by method parameter
 * @param headers Headers for the request
 *
 * @returns $ReturnType, if the request was successful, otherwise undefined
 */
export const getDataWithCSRF = async <$ReturnType>(
    url: string,
    method?: Method,
    data?: unknown,
    headers?: HeadersInit,
    showErrorToast = false
): Promise<$ReturnType | undefined> => {
    const CSRF = {
        'X-CSRFToken': csrfToken()
    };
    return getFromAPI(url, method, data, headers ? { ...headers, ...CSRF } : CSRF, showErrorToast);
};
