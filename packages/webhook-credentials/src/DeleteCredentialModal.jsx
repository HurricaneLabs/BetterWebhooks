import React, { useState, useRef } from 'react';

import Layout from '@splunk/react-icons/Layout';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import P from '@splunk/react-ui/Paragraph';

import { deleteCredential } from './http_utils';

function DeleteCredentialModal(props) {
    const modalToggle = useRef(null);

    const [open, setOpen] = useState(false);

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

    const handleSubmit = (event) => {
        event.preventDefault();
        deleteCredential(props.name, props.app).then(props.setLoaded(false)).then(setOpen(false));
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
                onRequestClose={handleRequestClickAway}
                open={open}
                returnFocus={modalToggle}
                style={{ width: '600px' }}
            >
                <form onSubmit={handleSubmit}>
                    <Modal.Header
                        onRequestClose={handleRequestClose}
                        title={`Delete credential`}
                        icon={<Layout width="100%" height="100%" />}
                    />

                    <Modal.Body>
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
                </form>
            </Modal>
        </>
    );
}

export default DeleteCredentialModal;
