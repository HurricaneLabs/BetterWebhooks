import React, { useState, useRef } from 'react';

import Layout from '@splunk/react-icons/Layout';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Modal from '@splunk/react-ui/Modal';
import Text from '@splunk/react-ui/Text';

import GenericCredForm from './CredentialForms';

import { saveExistingCredential } from './http_utils';

function EditCredentialModal(props) {
    const modalToggle = useRef(null);

    const [open, setOpen] = useState(false);

    const [credential, setCredential] = useState(props.cred);

    const handleRequestOpen = () => {
        setOpen(true);
    };

    const handleRequestClose = () => {
        setOpen(false);
    };

    // react-ui 5 draws the X button in Modal.Header but reports the click here.
    const handleModalRequestClose = ({ reason }) => {
        if (reason === 'escapeKey' || reason === 'clickCloseButton') {
            handleRequestClose();
        }
    };

    const handleChangeUsername = (event) => {
        setUsername(event.target.value);
    };

    const handleChangePassword = (event) => {
        setPassword(event.target.value);
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        saveExistingCredential(credential, props.name);
        setOpen(false);
    };

    return (
        <>
            <Button onClick={handleRequestOpen} ref={modalToggle} label="Edit" />
            <Modal
                onRequestClose={handleModalRequestClose}
                open={open}
                returnFocus={modalToggle}
                style={{ width: '600px' }}
            >
                <form onSubmit={handleSubmit}>
                    <Modal.Header
                        title="Edit credential"
                        icon={<Layout width={20} height={20} />}
                    />

                    <Modal.Body>
                        <ControlGroup label="Name">
                            <Text disabled value={props.name} />
                        </ControlGroup>
                        <GenericCredForm
                            type={props.type}
                            cred={credential}
                            setCredential={setCredential}
                        />
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

export default EditCredentialModal;
