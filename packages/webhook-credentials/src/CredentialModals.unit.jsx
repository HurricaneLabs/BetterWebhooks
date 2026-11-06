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

import DeleteCredentialModal from './DeleteCredentialModal';
import EditCredentialModal from './EditCredentialModal';
import NewCredentialModal from './NewCredentialModal';
import fakeSplunkd from './fakeSplunkd';

// react-ui's ModalLayer only unmounts when its react-spring animation reports done, and in
// jsdom a close that lands mid-way through the open animation never does: the dialog
// stays mounted at opacity 0. Skipping animations makes open and close finish at once.
Globals.assign({ skipAnimation: true });

const cred = { name: 'smoketest', type: 'basic', username: 'user', password: 'pass' };

// The modals reach splunkd through fetch, which jsdom doesn't provide. Fake that
// boundary instead of mocking http_utils, so the real request code still runs.
let splunkd;
beforeEach(() => {
    splunkd = fakeSplunkd([cred]);
    global.fetch = splunkd.fetch;
});

afterEach(() => {
    delete global.fetch;
});

const modals = [
    ['New', () => <NewCredentialModal setLoaded={() => {}} />, 'New Credential'],
    [
        'Edit',
        () => (
            <EditCredentialModal
                name={cred.name}
                type={cred.type}
                cred={cred}
                setLoaded={() => {}}
            />
        ),
        'Edit',
    ],
    [
        'Delete',
        () => <DeleteCredentialModal name={cred.name} app="BetterWebhooks" setLoaded={() => {}} />,
        'Delete',
    ],
];

// Renders the modal's trigger, clicks it, and waits for the dialog to open.
async function openModal(renderModal, triggerLabel) {
    render(renderModal());
    const trigger = screen.getByRole('button', { name: triggerLabel });
    fireEvent.click(trigger);
    const dialog = await screen.findByRole('dialog');
    return { trigger, dialog };
}

describe.each(modals)('%sCredentialModal', (_, renderModal, triggerLabel) => {
    it('closes on the X button', async () => {
        const { dialog } = await openModal(renderModal, triggerLabel);
        fireEvent.click(within(dialog).getByRole('button', { name: 'Close' }));
        await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
    });

    it('closes on Escape', async () => {
        await openModal(renderModal, triggerLabel);
        fireEvent.keyDown(document.activeElement, { key: 'Escape' });
        await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
    });

    it('closes on Cancel', async () => {
        const { dialog } = await openModal(renderModal, triggerLabel);
        fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));
        await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
    });

    // react-ui 5 sizes a header icon from its own props, so "100%" drew it 552px wide.
    it('draws a 20px header icon', async () => {
        const { dialog } = await openModal(renderModal, triggerLabel);
        const icon = dialog.querySelector('[data-test="header"] > svg');
        expect(icon).toHaveAttribute('width', '20');
        expect(icon).toHaveAttribute('height', '20');
    });

    it('returns focus to its trigger after closing', async () => {
        const { trigger, dialog } = await openModal(renderModal, triggerLabel);
        // Focus has to leave the trigger first, or this test passes without returnFocus.
        await waitFor(() => expect(dialog).toContainElement(document.activeElement));
        fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));
        await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
        await waitFor(() => expect(trigger).toHaveFocus());
    });
});

describe('DeleteCredentialModal', () => {
    it('does not delete the credential when closed with the X button', async () => {
        const { dialog } = await openModal(modals[2][1], 'Delete');
        fireEvent.click(within(dialog).getByRole('button', { name: 'Close' }));
        await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
        expect(splunkd.requests.map(({ method }) => method)).not.toContain('DELETE');
    });
});

// Edit and Delete each send one request. Each must wait for splunkd's answer: close on
// success, and on failure show why and stay open (#28, and the edit save that was never
// awaited). splunkd answers in XML unless asked for JSON, so these also catch a request
// that forgets output_mode=json.
const requestModals = [
    ['Edit', 'POST', 'Submit'],
    ['Delete', 'DELETE', 'Delete'],
];

describe.each(requestModals)('%sCredentialModal request', (label, method, submitLabel) => {
    const renderModal = modals.find(([name]) => name === label)[1];

    async function submit() {
        const opened = await openModal(renderModal, label);
        fireEvent.click(within(opened.dialog).getByRole('button', { name: submitLabel }));
        return opened;
    }

    it('closes when splunkd accepts it', async () => {
        await submit();
        await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
    });

    it("shows splunkd's error and stays open when it fails", async () => {
        splunkd.fail[method] = 'Insufficient permissions';
        const { dialog } = await submit();
        expect(await within(dialog).findByText('Insufficient permissions')).toBeVisible();
        expect(screen.getByRole('dialog')).toBe(dialog);
    });

    it('clears the error when reopened', async () => {
        splunkd.fail[method] = 'Insufficient permissions';
        const { trigger, dialog } = await submit();
        await within(dialog).findByText('Insufficient permissions');
        fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));
        await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
        fireEvent.click(trigger);
        const reopened = await screen.findByRole('dialog');
        expect(within(reopened).queryByText('Insufficient permissions')).not.toBeInTheDocument();
    });

    // A proxy in front of splunkd can answer with an HTML error page, which isn't JSON.
    it('shows the default message when the error is not JSON', async () => {
        const defaultMessage = {
            POST: 'An error occurred while updating existing credential',
            DELETE: 'An error occurred while deleting credential',
        }[method];
        splunkd.badGateway[method] = true;
        const { dialog } = await submit();
        expect(await within(dialog).findByText(defaultMessage)).toBeVisible();
    });
});

describe('EditCredentialModal', () => {
    // #29: the form was seeded from props.cred once, so a cancelled edit came back.
    it('shows the saved values, not a cancelled edit, when reopened', async () => {
        const { trigger, dialog } = await openModal(modals[1][1], 'Edit');
        const username = within(dialog).getByRole('textbox', { name: 'Username' });
        fireEvent.change(username, { target: { value: 'abandoned' } });
        fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));
        await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
        fireEvent.click(trigger);
        const reopened = await screen.findByRole('dialog');
        expect(within(reopened).getByRole('textbox', { name: 'Username' })).toHaveValue('user');
    });
});
