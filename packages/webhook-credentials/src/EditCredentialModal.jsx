import React, { useState, useRef } from 'react';
import PropTypes from 'prop-types';

import Layout from '@splunk/react-icons/Layout';
import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Modal from '@splunk/react-ui/Modal';
import Text from '@splunk/react-ui/Text';

import GenericCredForm from './CredentialForms';

import { saveExistingCredential } from './http_utils';
import { ModalForm } from './WebhookCredentialsStyles';

function EditCredentialModal(props) {
    const modalToggle = useRef(null);

    const [open, setOpen] = useState(false);

    const [credential, setCredential] = useState(props.cred);
    const [error, setError] = useState();

    // Start from the listed credential every time, not from an earlier cancelled edit (#29).
    const handleRequestOpen = () => {
        setCredential(props.cred);
        setError(null);
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

    // Close and reload only once splunkd confirms the save; on failure, stay open and
    // say why. The reload keeps props.cred current for the next open.
    const handleSubmit = async (event) => {
        event.preventDefault();
        try {
            await saveExistingCredential(credential, props.name, props.app);
            setOpen(false);
            props.setLoaded(false);
        } catch (err) {
            setError(err.message || String(err));
        }
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
                <ModalForm onSubmit={handleSubmit}>
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
                            error={error}
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
                </ModalForm>
            </Modal>
        </>
    );
}

EditCredentialModal.propTypes = {
    name: PropTypes.string.isRequired,
    app: PropTypes.string.isRequired,
    type: PropTypes.string,
    cred: PropTypes.object.isRequired,
    setLoaded: PropTypes.func.isRequired,
};

export default EditCredentialModal;
