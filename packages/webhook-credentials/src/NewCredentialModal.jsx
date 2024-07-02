import React, { useState, useRef } from 'react';

import Layout from '@splunk/react-icons/Layout';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import Select from '@splunk/react-ui/Select';
import Plus from '@splunk/react-icons/Plus';
import Text from '@splunk/react-ui/Text';
import ControlGroup from '@splunk/react-ui/ControlGroup';

import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';

import GenericCredForm from './CredentialForms';

const iconProps = { width: 20, height: 20 };

const passwordsEndpoint =
    '/en-US/splunkd/__raw/servicesNS/nobody/BetterWebhooks/storage/passwords';

async function saveNewCredential(credential, name) {
    // this function can be used to retrieve passwords if that becomes necessary in your app
    const fetchInit = defaultFetchInit;
    fetchInit.method = 'POST';

    const n = await fetch(`${passwordsEndpoint}/better_webhooks`, {
        ...fetchInit,
        body: `password=${JSON.stringify(credential)}&name=${name}&realm=better_webhooks`,
    })
        .then(handleResponse(200))
        .catch(handleError('error'))
        .catch((err) => (err instanceof Object ? 'error' : err)); // handleError sometimes returns an Object;
    return n;
}



function NewCredentialModal(props) {
    const modalToggle = useRef(null);

    const [open, setOpen] = useState(false);

    const [credType, setCredType] = useState();
    const [name, setName] = useState();
    const [credential, setCredential] = useState({ name: "", username: "", password: "", header_name: "", header_value: "", hmac_secret: "", hmac_hash_function: "sha1", hmac_digest_type: "b64", hmac_sig_header: "", hmac_time_header: "" });


    const handleRequestOpen = () => {
        setOpen(true);
    };

    const handleRequestClose = () => {
        setOpen(false);
    };

    const handleRequestClickAway = ({ reason }) => {
        if (reason === 'escapeKey') {
            setOpen(false);
        }
    };

    const handleChangeCredType = (event, { value }) => {
        setCredType(value);
    }

    const handleChangeName = (event) => {
        setName(event.target.value);
    }



    const handleSubmit = (event) => {
        event.preventDefault();
        saveNewCredential(credential, name)
            .then(props.setLoaded(false))
            .then(setOpen(false));
    }

    return (
        <>
            <Button appearance="primary" icon={<Plus {...iconProps} />} onClick={handleRequestOpen} ref={modalToggle} label="New Credential" />
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
                            <Text
                                onChange={handleChangeName}
                            />

                        </ControlGroup>
                        <GenericCredForm type={credType} cred={credential} setCredential={setCredential} />
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