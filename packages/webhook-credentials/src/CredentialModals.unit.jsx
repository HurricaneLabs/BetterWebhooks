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

// react-ui's ModalLayer only unmounts when its react-spring animation reports done, and in
// jsdom a close that lands mid-way through the open animation never does: the dialog
// stays mounted at opacity 0. Skipping animations makes open and close finish at once.
Globals.assign({ skipAnimation: true });

// The modals reach splunkd through fetch, which jsdom doesn't provide. Fake that
// boundary instead of mocking http_utils, so the real request code still runs.
// NewCredentialModal lists apps on mount, so every call gets an apps-shaped reply.
beforeEach(() => {
    global.fetch = jest.fn(() =>
        Promise.resolve({
            status: 200,
            json: () => Promise.resolve({ entry: [{ name: 'BetterWebhooks' }] }),
        })
    );
});

afterEach(() => {
    delete global.fetch;
});

const cred = { name: 'smoketest', type: 'basic', username: 'user', password: 'pass' };

const modals = [
    ['New', () => <NewCredentialModal setLoaded={() => {}} />, 'New Credential'],
    ['Edit', () => <EditCredentialModal name={cred.name} type={cred.type} cred={cred} />, 'Edit'],
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
        const methods = global.fetch.mock.calls.map(([, init]) => init && init.method);
        expect(methods).not.toContain('DELETE');
    });
});
