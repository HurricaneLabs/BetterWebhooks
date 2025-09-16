import React, { useState, useRef, useEffect } from 'react';

import Layout from '@splunk/react-icons/Layout';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import Select from '@splunk/react-ui/Select';
import Plus from '@splunk/react-icons/Plus';
import Text from '@splunk/react-ui/Text';
import Switch from '@splunk/react-ui/Switch';
import ControlGroup from '@splunk/react-ui/ControlGroup';

import { saveNewCredential, updateSharing, getApps } from './http_utils';

import GenericCredForm from './CredentialForms';

const iconProps = { width: 20, height: 20 };

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

    useEffect(() => {
        getApps().then(
            (apps) => setApps(apps),
            (error) => setError(error.message || String(error))
        );
    }, []);

    const createCredential = async () => {
        try {
            const resp = await saveNewCredential(credential, name, selectedApp);
            await updateSharing(resp.url, resp.author, selectedSharing, readPerms, writePerms);

            setOpen(false);
            setError(null);

            setTimeout(() => {
                props.setLoaded(false);
            }, 10);
        } catch (error) {
            console.error('Error creating credential:', error);
            setError(error.message || String(error));
        }
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        await createCredential();
    };

    return (
        <>
            <Button
                appearance="primary"
                icon={<Plus {...iconProps} />}
                onClick={() => setOpen(true)}
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
                            <Select onChange={(event, { value }) => setCredType(value)}>
                                <Select.Option label="HTTP Basic Auth" value="basic" />
                                <Select.Option label="Custom HTTP Header" value="header" />
                                <Select.Option label="HMAC Secret" value="hmac" />
                            </Select>
                        </ControlGroup>
                        <ControlGroup label="Name">
                            <Text onChange={(event) => setName(event.target.value)} />
                        </ControlGroup>
                        <GenericCredForm
                            type={credType}
                            cred={credential}
                            setCredential={setCredential}
                            error={error}
                        />

                        <Switch
                            value="advanced"
                            onClick={() => setAdvanced((current) => !current)}
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
                                        onChange={(event, { value }) => setSelectedApp(value)}
                                    >
                                        {apps.map((app) => (
                                            <Select.Option key={app} label={app} value={app} />
                                        ))}
                                    </Select>
                                </ControlGroup>
                                <ControlGroup
                                    label="Sharing"
                                    tooltip="Control if the credential is shared globally, at app-level, or not at all"
                                >
                                    <Select
                                        defaultValue="global"
                                        onChange={(event, { value }) => setSelectedSharing(value)}
                                    >
                                        <Select.Option label="Global" value="global" />
                                        <Select.Option label="App" value="app" />
                                        <Select.Option label="Private" value="user" />
                                    </Select>
                                </ControlGroup>
                                <ControlGroup
                                    label="Read permissions"
                                    tooltip="e.g. '*', 'admin', or 'admin, power'"
                                >
                                    <Text
                                        onChange={(event) => setReadPerms(event.target.value)}
                                        defaultValue="*"
                                    />
                                </ControlGroup>
                                <ControlGroup
                                    label="Write permissions"
                                    tooltip="e.g. '*', 'admin', or 'admin, power'"
                                >
                                    <Text
                                        onChange={(event) => setWritePerms(event.target.value)}
                                        defaultValue="*"
                                    />
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
