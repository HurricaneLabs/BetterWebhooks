import '@testing-library/jest-dom';
import React from 'react';
import {
    fireEvent,
    render,
    screen,
    waitFor,
    waitForElementToBeRemoved,
    within,
} from '@testing-library/react';
import { Globals } from '@react-spring/web';

import WebhookCredentials from './WebhookCredentials';
import fakeSplunkd from './fakeSplunkd';

// Open and close the modals at once; see CredentialModals.unit.jsx.
Globals.assign({ skipAnimation: true });

// Fake splunkd at the fetch boundary, so the page's real request code runs.
let splunkd;
beforeEach(() => {
    splunkd = fakeSplunkd([
        { name: 'smoketest', type: 'basic', username: 'user', password: 'pass' },
    ]);
    global.fetch = splunkd.fetch;
});

afterEach(() => {
    delete global.fetch;
});

const credentialReads = () =>
    splunkd.requests.filter(
        ({ url, method }) => method === 'GET' && url.includes('/storage/passwords')
    );

// Waits for a reload of the list to finish.
const reloaded = () =>
    waitFor(() => expect(screen.queryByText(/Loading credentials/)).not.toBeInTheDocument());

describe('WebhookCredentials', () => {
    it('renders without crashing and shows the description text', async () => {
        render(<WebhookCredentials />);
        await waitFor(() =>
            expect(
                screen.getByText(/Define any credentials your webhooks need here/i)
            ).toBeInTheDocument()
        );
    });

    it('lists the stored credentials, reading them once', async () => {
        render(<WebhookCredentials />);
        expect(await screen.findByText('smoketest')).toBeInTheDocument();
        await reloaded();
        expect(credentialReads()).toHaveLength(1);
    });

    // The load wasn't awaited, so its error never reached the page.
    it('shows why loading failed', async () => {
        splunkd.fail.GET = 'Insufficient permissions';
        render(<WebhookCredentials />);
        expect(await screen.findByText(/Insufficient permissions/)).toBeInTheDocument();
        expect(screen.queryByText(/No credentials found/)).not.toBeInTheDocument();
    });

    it('shows the default message when the load error is not JSON', async () => {
        splunkd.badGateway.GET = true;
        render(<WebhookCredentials />);
        expect(
            await screen.findByText(/An error occurred while getting credentials/)
        ).toBeInTheDocument();
    });

    // #28: the list reloaded while the DELETE was still in flight, so the row stayed.
    it('removes a deleted credential from the list', async () => {
        let finishDelete;
        splunkd.deleteGate = new Promise((resolve) => {
            finishDelete = resolve;
        });
        render(<WebhookCredentials />);
        fireEvent.click(await screen.findByRole('button', { name: 'Delete' }));
        const dialog = await screen.findByRole('dialog');
        fireEvent.click(within(dialog).getByRole('button', { name: 'Delete' }));
        await waitFor(() =>
            expect(splunkd.requests.some(({ method }) => method === 'DELETE')).toBe(true)
        );
        // While the DELETE is in flight: no reload yet, and the dialog stays open.
        expect(credentialReads()).toHaveLength(1);
        expect(screen.getByText('smoketest')).toBeInTheDocument();
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        finishDelete();
        await waitForElementToBeRemoved(() => screen.queryByText('smoketest'));
        expect(screen.getByText(/No credentials found/)).toBeInTheDocument();
    });

    // The form resets from the listed credential on open, so the list has to reload
    // after a save or reopening shows the old values. The save has to go to the app the
    // credential is stored in: from any other app, splunkd can't see an App credential.
    it.each([
        ['BetterWebhooks', 'global'],
        ['BetterWebhooks', 'app'],
        ['search', 'global'],
        ['search', 'app'],
    ])(
        'shows the saved values when Edit is reopened after a save (%s, %s sharing)',
        async (app, sharing) => {
            splunkd = fakeSplunkd([
                {
                    name: 'smoketest',
                    type: 'basic',
                    username: 'user',
                    password: 'pass',
                    app,
                    sharing,
                },
            ]);
            global.fetch = splunkd.fetch;
            render(<WebhookCredentials />);
            fireEvent.click(await screen.findByRole('button', { name: 'Edit' }));
            const dialog = await screen.findByRole('dialog');
            fireEvent.change(within(dialog).getByRole('textbox', { name: 'Username' }), {
                target: { value: 'newuser' },
            });
            fireEvent.click(within(dialog).getByRole('button', { name: 'Submit' }));
            await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
            await reloaded();
            fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
            const reopened = await screen.findByRole('dialog');
            expect(within(reopened).getByRole('textbox', { name: 'Username' })).toHaveValue(
                'newuser'
            );
        }
    );
});
