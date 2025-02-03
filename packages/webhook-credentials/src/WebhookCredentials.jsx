import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import Table from '@splunk/react-ui/Table';
import P from '@splunk/react-ui/Paragraph';
import ExclamationSquare from '@splunk/react-icons/ExclamationSquare';

import EditCredentialModal from './EditCredentialModal';
import NewCredentialModal from './NewCredentialModal';
import DeleteCredentialModal from './DeleteCredentialModal';

import {
    StyledContainer,
    StyledHeader,
    AlignRight,
    DescriptionText,
} from './WebhookCredentialsStyles';
import { getDefaultFetchInit, handleResponse } from '@splunk/splunk-utils/fetch';
import { getUserTheme } from '@splunk/splunk-utils/themes';

getUserTheme().then((mode) => {
    if (mode == 'dark') {
        document.body.style.backgroundColor = '#171d21';
    }
});

const propTypes = {
    name: PropTypes.string,
};

const passwordsEndpoint = '/en-US/splunkd/__raw/servicesNS/nobody/-/storage/passwords';

async function getCredentials() {
    // this function can be used to retrieve passwords if that becomes necessary in your app
    const fetchInit = getDefaultFetchInit();
    fetchInit.method = 'GET';
    const creds = await fetch(`${passwordsEndpoint}?output_mode=json`, {
        ...fetchInit,
    }).then(handleResponse(200));

    return creds;
}

const credTypeMap = {
    basic: 'HTTP Basic Auth',
    header: 'Custom HTTP Header',
    hmac: 'HMAC Secret',
    unknown: 'Unknown (failed to parse)',
};

const WebhookCredentials = () => {
    const [loaded, setLoaded] = useState(false);
    const [credentials, setCredentials] = useState([]);
    const [error, setError] = useState();

    useEffect(() => {
        getCredentials().then((r) => {
            const filtered = r.entry.filter((entry) => {
                if ('realm' in entry.content && entry.content.realm == 'better_webhooks') {
                    return true;
                }
                return false;
            });
            const list = filtered.map((entry) => {
                if ('realm' in entry.content && entry.content.realm == 'better_webhooks') {
                    try {
                        const cred_obj = JSON.parse(entry.content.clear_password);
                        cred_obj.name = entry.content.username;
                        cred_obj.app = entry.acl.app;
                        cred_obj.sharing = entry.acl.sharing;
                        cred_obj.owner = entry.acl.owner;
                        return cred_obj;
                    } catch (e) {
                        console.log('Failed to parse credential: ' + entry.content.clear_password);
                        return {
                            name: entry.content.username,
                            app: entry.acl.app,
                            sharing: entry.acl.sharing,
                            type: 'unknown',
                        };
                    }
                }
            });
            setCredentials(list);
            setLoaded(true);
        })
        .catch(error_resp => {
            setError("Failed to list credentials. Do you have either the list_storage_passwords or admin_all_objects capability?");
        });
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
            {error && (
                <>
                    <br />
                    <P>
                        <ExclamationSquare style={{ color: 'red' }}/> {error}
                    </P>
                </>
            )}
            
            {!error && credentials.length == 0 && (
                <>
                    <br />
                    <P>
                        <ExclamationSquare /> No credentials found. Add one by clicking "New
                        Credential".
                    </P>
                </>
            )}
        </StyledContainer>
    );
};

WebhookCredentials.propTypes = propTypes;

export default WebhookCredentials;
