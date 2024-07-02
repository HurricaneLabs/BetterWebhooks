import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import Table from '@splunk/react-ui/Table';
import P from '@splunk/react-ui/Paragraph';
import ExclamationSquare from '@splunk/react-icons/ExclamationSquare';


import EditCredentialModal from './EditCredentialModal';
import NewCredentialModal from './NewCredentialModal';
import DeleteCredentialModal from './DeleteCredentialModal';

import { StyledContainer, StyledHeader, AlignRight, DescriptionText} from './WebhookCredentialsStyles';
import { defaultFetchInit, handleResponse } from '@splunk/splunk-utils/fetch';
import { getUserTheme } from '@splunk/splunk-utils/themes';

getUserTheme().then((mode) => {
    if (mode == 'dark') {
        document.body.style.backgroundColor = '#171d21';
    }
});

const propTypes = {
    name: PropTypes.string,
};

const passwordsEndpoint =
    '/en-US/splunkd/__raw/servicesNS/nobody/BetterWebhooks/storage/passwords';

async function getCredentials() {
    // this function can be used to retrieve passwords if that becomes necessary in your app
    const fetchInit = defaultFetchInit
    fetchInit.method = 'GET';
    const n = await fetch(`${passwordsEndpoint}?output_mode=json`, {
        ...fetchInit,
    }).then(handleResponse(200));

    return n;
}


const credTypeMap = {
    basic: "HTTP Basic Auth",
    header: "Custom HTTP Header",
    hmac: "HMAC Secret"
};

const WebhookCredentials = () => {
    const [loaded, setLoaded] = useState(false);
    const [credentials, setCredentials] = useState([])



    useEffect(() => {
        getCredentials().then((r) => {
            const list = r.entry.map((entry) => {
                console.log(entry.content);
                if ("realm" in entry.content && entry.content.realm == "better_webhooks") {
                    try {
                        const cred_obj = JSON.parse(entry.content.clear_password);
                        cred_obj.name = entry.content.username;
                        return cred_obj;
                    } catch (e) {
                        console.log("Failed to parse credential: " + entry.content.clear_password)
                    }
                }
            });

            setCredentials(list);
            setLoaded(true);
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
            <DescriptionText>Define any credentials your webhooks need here. Once defined, they will be selectable on the "Better Webhook" alert action page.</DescriptionText>

            <br />
            <Table>
                <Table.Head>
                    <Table.HeadCell>Name</Table.HeadCell>
                    <Table.HeadCell>Credential Type</Table.HeadCell>
                    <Table.HeadCell>Edit</Table.HeadCell>
                    <Table.HeadCell>Delete</Table.HeadCell>
                </Table.Head>
                <Table.Body>
                    {credentials.map((cred) => (
                        <Table.Row key={cred.name}>
                            <Table.Cell>{cred.name}</Table.Cell>
                            <Table.Cell>{credTypeMap[cred.type]}</Table.Cell>
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
                                    setLoaded={setLoaded}
                                />
                            </Table.Cell>
                        </Table.Row>
                    ))}
                </Table.Body>
            </Table>
            {credentials.length == 0 &&
                <>
                    <br />
                    <P><ExclamationSquare /> No credentials found. Add one by clicking "New Credential".</P>
                </>
            }

        </StyledContainer>
    );
};

WebhookCredentials.propTypes = propTypes;

export default WebhookCredentials;
