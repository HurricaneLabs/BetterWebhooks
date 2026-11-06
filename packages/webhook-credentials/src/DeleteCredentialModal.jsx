import React, { useState, useRef } from 'react';
import PropTypes from 'prop-types';

import Layout from '@splunk/react-icons/Layout';
import Button from '@splunk/react-ui/Button';
import Message from '@splunk/react-ui/Message';
import Modal from '@splunk/react-ui/Modal';
import P from '@splunk/react-ui/Paragraph';

import { deleteCredential } from './http_utils';
import { ModalForm } from './WebhookCredentialsStyles';

function DeleteCredentialModal(props) {
    const modalToggle = useRef(null);

    const [open, setOpen] = useState(false);
    const [error, setError] = useState();

    const handleRequestOpen = () => {
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

    // Close and reload only once splunkd confirms the delete; on failure, stay open and
    // say why (#28).
    const handleSubmit = async (event) => {
        event.preventDefault();
        try {
            await deleteCredential(props.name, props.app);
            setOpen(false);
            props.setLoaded(false);
        } catch (err) {
            setError(err.message || String(err));
        }
    };

    return (
        <>
            <Button
                appearance="destructive"
                onClick={handleRequestOpen}
                ref={modalToggle}
                label="Delete"
            />
            <Modal
                onRequestClose={handleModalRequestClose}
                open={open}
                returnFocus={modalToggle}
                style={{ width: '600px' }}
            >
                <ModalForm onSubmit={handleSubmit}>
                    <Modal.Header
                        title="Delete credential"
                        icon={<Layout width={20} height={20} />}
                    />

                    <Modal.Body>
                        {error && (
                            <Message appearance="fill" type="error">
                                {error}
                            </Message>
                        )}
                        <P>{`Are you sure you want to delete "${props.name}"?`}</P>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            appearance="secondary"
                            onClick={handleRequestClose}
                            label="Cancel"
                        />

                        <Button appearance="destructive" label="Delete" type="submit" />
                    </Modal.Footer>
                </ModalForm>
            </Modal>
        </>
    );
}

DeleteCredentialModal.propTypes = {
    name: PropTypes.string.isRequired,
    app: PropTypes.string.isRequired,
    setLoaded: PropTypes.func.isRequired,
};

export default DeleteCredentialModal;
