import { getDefaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';

export async function getApps() {
    const appsEndpoint = '/en-US/splunkd/__raw/services/apps/local?output_mode=json&count=0';

    try {
        const resp = await fetch(`${appsEndpoint}`, {
            ...getDefaultFetchInit(),
            method: 'GET',
        });
        const apps = await handleResponse(200)(resp);
        return apps.entry.map(({ name }) => name);
    } catch (error) {
        return handleError('An error occurred while getting apps')(error);
    }
}

export async function getCredentials() {
    const passwordsEndpoint = '/en-US/splunkd/__raw/servicesNS/nobody/-/storage/passwords';

    try {
        const resp = await fetch(
            `${passwordsEndpoint}?output_mode=json&count=0&search=realm%3D%22better_webhooks%22`,
            {
                ...getDefaultFetchInit(),
                method: 'GET',
            }
        );
        const creds = await handleResponse(200)(resp);
        return creds;
    } catch (error) {
        return handleError('An error occurred while getting credentials')(error);
    }
}

export async function saveNewCredential(credential, name, app) {
    const passwordsEndpoint = `/en-US/splunkd/__raw/servicesNS/nobody/${app}/storage/passwords`;

    const encoded = encodeURIComponent(JSON.stringify(credential));

    try {
        const resp = await fetch(`${passwordsEndpoint}`, {
            ...getDefaultFetchInit(),
            method: 'POST',
            body: `password=${encoded}&name=${name}&realm=better_webhooks&output_mode=json`,
        });

        const processedResp = await handleResponse(201)(resp);

        return { url: processedResp.entry[0].links.edit, author: processedResp.entry[0].author };
    } catch (error) {
        return handleError('An error occurred while saving new credential')(error);
    }
}

export async function saveExistingCredential(credential, name) {
    const passwordsEndpoint =
        '/en-US/splunkd/__raw/servicesNS/nobody/BetterWebhooks/storage/passwords';

    const encoded = encodeURIComponent(JSON.stringify(credential));

    try {
        const resp = await fetch(`${passwordsEndpoint}/better_webhooks:${name}:`, {
            ...getDefaultFetchInit(),
            method: 'POST',
            body: `password=${encoded}`,
        });

        const processedResp = await handleResponse(200)(resp);
        return processedResp;
    } catch (error) {
        return handleError('An error occurred while updating existing credential')(error);
    }
}

// #28: callers can't tell a failed delete from a success. BWH-V2-5 decides what this
// resolves to, so the return stays as it is.
// eslint-disable-next-line consistent-return
export async function deleteCredential(name, app) {
    const passwordsEndpoint = `/en-US/splunkd/__raw/servicesNS/nobody/${app}/storage/passwords`;

    try {
        const resp = await fetch(`${passwordsEndpoint}/better_webhooks:${name}:`, {
            ...getDefaultFetchInit(),
            method: 'DELETE',
            output_mode: 'json',
        });

        await handleResponse(200)(resp);
    } catch (error) {
        return handleError('An error occurred while deleting credential')(error);
    }
}

export async function updateSharing(credentialUrl, author, sharing, readPerms, writePerms) {
    const configUrl = credentialUrl.replace(
        '/storage/passwords/',
        '/configs/conf-passwords/credential%3A'
    );
    const fullUrl = `/en-US/splunkd/__raw${configUrl}/acl`;

    try {
        const resp = await fetch(fullUrl, {
            ...getDefaultFetchInit(),
            method: 'POST',
            body: new URLSearchParams({
                sharing,
                owner: author,
                'perms.read': readPerms,
                'perms.write': writePerms,
                output_mode: 'json',
            }),
        });
        await handleResponse(200)(resp);
        return { success: true };
    } catch (error) {
        return handleError('An error occurred while updating sharing')(error);
    }
}
