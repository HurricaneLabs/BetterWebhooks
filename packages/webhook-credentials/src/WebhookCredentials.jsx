import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import Table from '@splunk/react-ui/Table';
import P from '@splunk/react-ui/Paragraph';

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
import { getUserTheme } from '@splunk/splunk-utils/themes';

getUserTheme().then((mode) => {
    if (mode == 'dark') {
        document.body.style.backgroundColor = '#171d21';
    }
});

const propTypes = {
    name: PropTypes.string,
};

const credTypeMap = {
    basic: 'HTTP Basic Auth',
    header: 'Custom HTTP Header',
    hmac: 'HMAC Secret',
    unknown: 'Unknown (failed to parse)',
};

function formatCredential(entry) {
    try {
        const cred_obj = JSON.parse(entry.content.clear_password);
        cred_obj.name = entry.content.username;
        cred_obj.app = entry.acl.app;
        cred_obj.sharing = entry.acl.sharing;
        cred_obj.owner = entry.acl.owner;
        return cred_obj;
    } catch (error) {
        console.log('Failed to parse credential: ' + entry.content.clear_password);
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

    useEffect(() => {
        async function getAndFormatCredentials() {
            const creds = await getCredentials();
            const filtered = creds.entry
                .filter((entry) => {
                    // Skip credentials from other realms
                    return 'realm' in entry.content && entry.content.realm === 'better_webhooks';
                })
                .map((entry) => {
                    const formatted = formatCredential(entry);
                    return formatted;
                });
            setCredentials(filtered);
        }
        try {
            getAndFormatCredentials();
        } catch (error) {
            setError(error.message || String(error));
        }
        setLoaded(true);
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
                selectable on the "Better Webhook" alert action page.
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
                        <Table.Row key={cred.name}>
                            <Table.Cell>{cred.name}</Table.Cell>
                            <Table.Cell>{credTypeMap[cred.type]}</Table.Cell>
                            <Table.Cell>{cred.app}</Table.Cell>
                            <Table.Cell>{cred.owner}</Table.Cell>
                            <Table.Cell>{cred.sharing}</Table.Cell>
                            <Table.Cell>
                                <EditCredentialModal
                                    key={cred.name}
                                    name={cred.name}
                                    type={cred.type}
                                    cred={cred}
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

WebhookCredentials.propTypes = propTypes;

export default WebhookCredentials;
