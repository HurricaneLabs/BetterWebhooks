import React, { useState, useEffect } from 'react';
import Table from '@splunk/react-ui/Table';

import EditCredentialModal from './EditCredentialModal';
import NewCredentialModal from './NewCredentialModal';
import DeleteCredentialModal from './DeleteCredentialModal';
import StatusMessage from './StatusMessage';

import {
    StyledContainer,
    StyledHeader,
    AlignRight,
    DescriptionText,
} from './WebhookCredentialsStyles';
import { getCredentials } from './http_utils';

const credTypeMap = {
    basic: 'HTTP Basic Auth',
    header: 'Custom HTTP Header',
    hmac: 'HMAC Secret',
    oauth: 'OAuth Client Credential',
    unknown: 'Unknown (failed to parse)',
};

function formatCredential(entry) {
    try {
        const credObj = JSON.parse(entry.content.clear_password);
        credObj.name = entry.content.username;
        credObj.app = entry.acl.app;
        credObj.sharing = entry.acl.sharing;
        credObj.owner = entry.acl.owner;
        return credObj;
    } catch (error) {
        return {
            name: entry.content.username,
            app: entry.acl.app,
            sharing: entry.acl.sharing,
            owner: entry.acl.owner,
            type: 'unknown',
        };
    }
}

const WebhookCredentials = () => {
    const [loaded, setLoaded] = useState(false);
    const [credentials, setCredentials] = useState([]);
    const [error, setError] = useState();

    // Children call setLoaded(false) to ask for a reload. Load only then: setting it back
    // to true re-runs this effect, which must not fetch a second time.
    useEffect(() => {
        if (loaded) {
            return;
        }
        async function getAndFormatCredentials() {
            try {
                const creds = await getCredentials();
                const filtered = creds.entry
                    .filter((entry) => {
                        // Skip credentials from other realms
                        return (
                            'realm' in entry.content && entry.content.realm === 'better_webhooks'
                        );
                    })
                    .map((entry) => {
                        const formatted = formatCredential(entry);
                        return formatted;
                    });
                setCredentials(filtered);
                setError(undefined);
            } catch (err) {
                setError(err.message || String(err));
            }
            setLoaded(true);
        }
        getAndFormatCredentials();
    }, [loaded]);

    return (
        <StyledContainer>
            <StyledHeader>
                Credentials
                <AlignRight>
                    <NewCredentialModal setLoaded={setLoaded} />
                </AlignRight>
            </StyledHeader>
            <DescriptionText>
                Define any credentials your webhooks need here. Once defined, they will be
                selectable on the &quot;Better Webhook&quot; alert action page.
            </DescriptionText>

            <br />
            <Table>
                <Table.Head>
                    <Table.HeadCell>Name</Table.HeadCell>
                    <Table.HeadCell>Credential Type</Table.HeadCell>
                    <Table.HeadCell>App</Table.HeadCell>
                    <Table.HeadCell>Owner</Table.HeadCell>
                    <Table.HeadCell>Sharing</Table.HeadCell>
                    <Table.HeadCell>Edit</Table.HeadCell>
                    <Table.HeadCell>Delete</Table.HeadCell>
                </Table.Head>
                <Table.Body>
                    {credentials.map((cred) => (
                        <Table.Row key={`${cred.app}:${cred.name}`}>
                            <Table.Cell>{cred.name}</Table.Cell>
                            <Table.Cell>{credTypeMap[cred.type]}</Table.Cell>
                            <Table.Cell>{cred.app}</Table.Cell>
                            <Table.Cell>{cred.owner}</Table.Cell>
                            <Table.Cell>{cred.sharing}</Table.Cell>
                            <Table.Cell>
                                <EditCredentialModal
                                    key={cred.name}
                                    name={cred.name}
                                    app={cred.app}
                                    type={cred.type}
                                    cred={cred}
                                    setLoaded={setLoaded}
                                />
                            </Table.Cell>
                            <Table.Cell>
                                <DeleteCredentialModal
                                    name={cred.name}
                                    app={cred.app}
                                    setLoaded={setLoaded}
                                />
                            </Table.Cell>
                        </Table.Row>
                    ))}
                </Table.Body>
            </Table>
            <StatusMessage error={error} loaded={loaded} credentialsCount={credentials.length} />
        </StyledContainer>
    );
};

export default WebhookCredentials;
