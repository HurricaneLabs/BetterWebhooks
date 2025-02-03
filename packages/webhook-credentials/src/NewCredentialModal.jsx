import React, { useState, useRef, useEffect, useCallback } from 'react';

import Layout from '@splunk/react-icons/Layout';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import Select from '@splunk/react-ui/Select';
import Plus from '@splunk/react-icons/Plus';
import Text from '@splunk/react-ui/Text';
import Switch from '@splunk/react-ui/Switch';
import ControlGroup from '@splunk/react-ui/ControlGroup';


import { getDefaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';

import GenericCredForm from './CredentialForms';

const iconProps = { width: 20, height: 20 };

async function saveNewCredential(credential, name, app) {
    const passwordsEndpoint = `/en-US/splunkd/__raw/servicesNS/nobody/${app}/storage/passwords`;
    const fetchInit = getDefaultFetchInit();
    fetchInit.method = 'POST';

    const resp = await fetch(`${passwordsEndpoint}`, {
        ...fetchInit,
        body: `password=${JSON.stringify(
            credential
        )}&name=${name}&realm=better_webhooks&output_mode=json`,
    })
        .then(handleResponse(201))
        .catch(handleError('error'))
        .catch((err) => (err instanceof Object ? 'error' : err)); // handleError sometimes returns an Object;
    // Return API path to the new credential so we can potentially change sharing
    return { url: resp.entry[0].links.edit, author: resp.entry[0].author };
}

async function updateSharing(credential_url, author, sharing, readPerms, writePerms) {
    let config_url = credential_url.replace(
        '/storage/passwords/',
        '/configs/conf-passwords/credential%3A'
    );
    const full_url = `/en-US/splunkd/__raw${config_url}/acl`;
    const fetchInit = getDefaultFetchInit();
    fetchInit.method = 'POST';

    const resp = await fetch(full_url, {
        ...fetchInit,
        body: new URLSearchParams({
            sharing: sharing,
            owner: author,
            'perms.read': readPerms,
            'perms.write': writePerms,
        }),
    })
        .then(handleResponse(201))
        .catch(handleError('error'))
        .catch((err) => (err instanceof Object ? 'error' : err)); // handleError sometimes returns an Object;

    return;
}

async function getApps() {
    const fetchInit = getDefaultFetchInit();
    const appsEndpoint = '/en-US/splunkd/__raw/services/apps/local?output_mode=json&count=0';

    fetchInit.method = 'GET';

    const apps = await fetch(`${appsEndpoint}`, {
        ...fetchInit,
    })
        .then(handleResponse(200))
        .catch(handleError('error'))
        .catch((err) => (err instanceof Object ? 'error' : err)); // handleError sometimes returns an Object;

    // Return only app names
    return apps.entry.map(({ name }) => name);
}

function NewCredentialModal(props) {
    const modalToggle = useRef(null);

    const [open, setOpen] = useState(false);

    const [credType, setCredType] = useState();
    const [name, setName] = useState();
    const [credential, setCredential] = useState({
        name: '',
        username: '',
        password: '',
        header_name: '',
        header_value: '',
        hmac_secret: '',
        hmac_hash_function: 'sha1',
        hmac_digest_type: 'b64',
        hmac_sig_header: '',
        hmac_time_header: '',
    });
    const [advanced, setAdvanced] = useState(false);
    const [apps, setApps] = useState([]);
    const [selectedApp, setSelectedApp] = useState('BetterWebhooks');
    const [selectedSharing, setSelectedSharing] = useState('global');
    const [readPerms, setReadPerms] = useState('*');
    const [writePerms, setWritePerms] = useState('*');
    const [error, setError] = useState();

    const handleRequestOpen = () => {
        setOpen(true);
    };

    const handleRequestClose = () => {
        setOpen(false);
        setError(null);
    };

    const handleRequestClickAway = ({ reason }) => {
        if (reason === 'escapeKey') {
            setOpen(false);
            setError(null);
        }
    };

    const handleChangeCredType = (event, { value }) => {
        setCredType(value);
    };

    const handleChangeName = (event) => {
        setName(event.target.value);
    };

    useEffect(() => {
        getApps().then((apps) => setApps(apps));
    }, []);

    const handleSubmit = (event) => {
        event.preventDefault();

        saveNewCredential(credential, name, selectedApp)
            .then((ret) => {
                updateSharing(ret.url, ret.author, selectedSharing, readPerms, writePerms);
            }
            )
            .catch(error => {
                console.error('There was a problem with the fetch operation:', error);
                setError("Failed to create new credential. Do you have either the edit_storage_passwords or admin_all_objects capability?");
                // So that the next steps don't execute if this fails.
                // Surely there's a better way to do this but I'm not skilled with JS
                return Promise.reject(error);
            })
            .then(() => {
                setOpen(false);
                setError(null);
            })
            .then(() => {
                setTimeout(() => {
                    props.setLoaded(false);
                }, 10);
            });
            
    };

    const handleAdvancedClick = useCallback(() => {
        setAdvanced((current) => !current);
    }, []);

    const handleChangeApp = (event, { value }) => {
        setSelectedApp(value);
    };

    const handleChangeSharing = (event, { value }) => {
        setSelectedSharing(value);
    };

    const handleChangeReadPerms = (event) => {
        setReadPerms(event.target.value);
    };

    const handleChangeWritePerms = (event) => {
        setWritePerms(event.target.value);
    };

    return (
        <>
            <Button
                appearance="primary"
                icon={<Plus {...iconProps} />}
                onClick={handleRequestOpen}
                ref={modalToggle}
                label="New Credential"
            />
            <Modal
                onRequestClose={handleRequestClickAway}
                open={open}
                returnFocus={modalToggle}
                style={{ width: '600px' }}
            >
                <form onSubmit={handleSubmit}>
                    <Modal.Header
                        onRequestClose={handleRequestClose}
                        title="New credential"
                        icon={<Layout width="100%" height="100%" />}
                    />

                    <Modal.Body>
                        <ControlGroup label="Credential type">
                            <Select onChange={handleChangeCredType}>
                                <Select.Option label="HTTP Basic Auth" value="basic" />
                                <Select.Option label="Custom HTTP Header" value="header" />
                                <Select.Option label="HMAC Secret" value="hmac" />
                            </Select>
                        </ControlGroup>
                        <ControlGroup label="Name">
                            <Text onChange={handleChangeName} />
                        </ControlGroup>
                        <GenericCredForm
                            type={credType}
                            cred={credential}
                            setCredential={setCredential}
                            error={error}
                        />

                        <Switch
                            value="advanced"
                            onClick={handleAdvancedClick}
                            selected={advanced}
                            appearance="checkbox"
                        >
                            Advanced options
                        </Switch>
                        {advanced && (
                            <>
                                <ControlGroup
                                    label="App context"
                                    tooltip="Use this if you need to store your credentials in a separate app"
                                >
                                    <Select
                                        defaultValue="BetterWebhooks"
                                        onChange={handleChangeApp}
                                    >
                                        {apps.map((app) => (
                                            <Select.Option label={app} value={app} />
                                        ))}
                                    </Select>
                                </ControlGroup>
                                <ControlGroup
                                    label="Sharing"
                                    tooltip="Control if the credential is shared globally, at app-level, or not at all"
                                >
                                    <Select defaultValue="global" onChange={handleChangeSharing}>
                                        <Select.Option label="Global" value="global" />
                                        <Select.Option label="App" value="app" />
                                        <Select.Option label="Private" value="user" />
                                    </Select>
                                </ControlGroup>
                                <ControlGroup
                                    label="Read permissions"
                                    tooltip="e.g. '*', 'admin', or 'admin, power'"
                                >
                                    <Text onChange={handleChangeReadPerms} defaultValue="*" />
                                </ControlGroup>
                                <ControlGroup
                                    label="Write permissions"
                                    tooltip="e.g. '*', 'admin', or 'admin, power'"
                                >
                                    <Text onChange={handleChangeWritePerms} defaultValue="*" />
                                </ControlGroup>
                            </>
                        )}
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            appearance="secondary"
                            onClick={handleRequestClose}
                            label="Cancel"
                        />

                        <Button appearance="primary" label="Submit" type="submit" />
                    </Modal.Footer>
                </form>
            </Modal>
        </>
    );
}

export default NewCredentialModal;
