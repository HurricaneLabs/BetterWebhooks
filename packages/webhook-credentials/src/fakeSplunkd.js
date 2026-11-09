// A fake of the splunkd endpoints the credentials page calls, for the unit tests. It
// replaces fetch, so the real request code in http_utils still runs. Like splunkd, it
// answers in XML unless the request asks for output_mode=json in its URL or body, so a
// request that forgets output_mode fails here the way it does in Splunk.
//
// It also follows splunkd's namespaces, as seen on Splunk 10.4. A request to
// servicesNS/nobody/<app> sees a Global credential from any app and an App credential
// only from its own app. It never sees a Private one, so neither does the listing.

const ENTITY = /\/storage\/passwords\/better_webhooks:([^:/?]+):/;
const NAMESPACE = /\/servicesNS\/[^/]+\/([^/]+)\/storage\/passwords/;

/** Returns a test for whether a stored credential is visible from servicesNS/nobody/<app>. */
function visibleFrom(app) {
    return (cred) =>
        cred.sharing === 'global' || (cred.sharing === 'app' && (app === '-' || cred.app === app));
}

function reply(status, body, asJson) {
    return {
        status,
        json: () =>
            asJson
                ? Promise.resolve(body)
                : Promise.reject(new SyntaxError('Unexpected token < in JSON at position 0')),
    };
}

// Stores a credential the way the page reads it back: the secret fields as JSON in
// clear_password, the rest in content and acl.
function toEntry({ name, app, sharing, owner, ...secret }) {
    return {
        content: {
            username: name,
            realm: 'better_webhooks',
            clear_password: JSON.stringify(secret),
        },
        acl: { app, sharing, owner },
    };
}

/**
 * Makes a fake splunkd holding the given credentials.
 *
 * Set `fail[method]` to an error message to make every storage/passwords request with
 * that method answer 500 with that message. Set `badGateway[method]` to make it answer 502
 * with an HTML page, as a proxy in front of splunkd does. Set `deleteGate` to a promise to hold each
 * DELETE until it resolves; the row is removed only then, as in splunkd.
 */
export default function fakeSplunkd(credentials = []) {
    const stored = credentials.map((cred) => ({
        app: 'BetterWebhooks',
        sharing: 'global',
        owner: 'nobody',
        ...cred,
    }));

    const splunkd = { requests: [], fail: {}, badGateway: {}, deleteGate: null };

    /** Answers one request the way splunkd would, and records it in `requests`. */
    splunkd.fetch = async (url, init = {}) => {
        const method = init.method || 'GET';
        const body = init.body ? String(init.body) : '';
        splunkd.requests.push({ url, method, body });
        const asJson = url.includes('output_mode=json') || body.includes('output_mode=json');
        const namespace = url.match(NAMESPACE);
        const visible = visibleFrom(namespace && namespace[1]);
        const listing = () => reply(200, { entry: stored.filter(visible).map(toEntry) }, asJson);

        if (url.includes('/apps/local')) {
            return reply(200, { entry: [{ name: 'BetterWebhooks' }] }, asJson);
        }
        if (url.endsWith('/acl')) {
            return reply(200, {}, asJson);
        }
        if (!url.includes('/storage/passwords')) {
            return reply(404, {}, asJson);
        }
        if (splunkd.badGateway[method]) {
            return reply(502, null, false);
        }
        if (splunkd.fail[method]) {
            return reply(
                500,
                { messages: [{ type: 'ERROR', text: splunkd.fail[method] }] },
                asJson
            );
        }

        const entity = url.match(ENTITY);
        const name = entity && decodeURIComponent(entity[1]);
        const index = stored.findIndex((cred) => cred.name === name && visible(cred));

        if (entity && index === -1) {
            const text = `A password does not exists for id="credential:better_webhooks:${name}:"`;
            return reply(404, { messages: [{ type: 'ERROR', text }] }, asJson);
        }
        if (entity && method === 'DELETE') {
            await splunkd.deleteGate;
            stored.splice(index, 1);
            return listing();
        }
        if (entity && method === 'POST') {
            const { app, sharing, owner } = stored[index];
            const secret = JSON.parse(new URLSearchParams(body).get('password'));
            stored[index] = { ...secret, name, app, sharing, owner };
            return reply(200, { entry: [toEntry(stored[index])] }, asJson);
        }
        if (method === 'GET') {
            return listing();
        }
        return reply(404, {}, asJson);
    };

    return splunkd;
}
