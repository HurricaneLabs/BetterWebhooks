import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import WebhookCredentials from './WebhookCredentials';

// WebhookCredentials.jsx calls getCredentials() on mount; it must be mocked so the
// component renders in jsdom. babel-jest hoists jest.mock above the imports.
jest.mock('./http_utils', () => ({
    getCredentials: () => Promise.resolve({ entry: [] }),
    getApps: () => Promise.resolve([]),
    saveNewCredential: () => Promise.resolve({}),
    saveExistingCredential: () => Promise.resolve({}),
    deleteCredential: () => Promise.resolve(),
    updateSharing: () => Promise.resolve({ success: true }),
}));

describe('WebhookCredentials', () => {
    it('renders without crashing and shows the description text', async () => {
        render(<WebhookCredentials />);
        await waitFor(() =>
            expect(
                screen.getByText(/Define any credentials your webhooks need here/i)
            ).toBeInTheDocument()
        );
    });
});
