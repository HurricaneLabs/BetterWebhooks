import React, { useState, useRef } from 'react';

import Text from '@splunk/react-ui/Text';
import Select from '@splunk/react-ui/Select';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Message from '@splunk/react-ui/Message';

function HTTPCredForm(props) {
    const handleChangeUsername = (event) => {
        let credential = {
            type: 'basic',
            username: event.target.value,
            password: props.cred.password,
        };
        props.setCredential(credential);
    };

    const handleChangePassword = (event) => {
        let credential = {
            type: 'basic',
            username: props.cred.username,
            password: event.target.value,
        };
        props.setCredential(credential);
    };
    return (
        <>
            <ControlGroup label="Username">
                <Text
                    value={props.cred.username}
                    autoComplete="off"
                    onChange={handleChangeUsername}
                />
            </ControlGroup>
            <ControlGroup label="Password" controlsLayout="fillJoin">
                <Text
                    value={props.cred.password}
                    passwordVisibilityToggle
                    type="password"
                    autoComplete="off"
                    canClear
                    onChange={handleChangePassword}
                />
            </ControlGroup>
        </>
    );
}

function HeaderCredForm(props) {
    const handleChangeHeaderName = (event) => {
        let credential = {
            type: 'header',
            header_name: event.target.value,
            header_value: props.cred.header_value,
        };
        props.setCredential(credential);
    };

    const handleChangeHeaderValue = (event) => {
        let credential = {
            type: 'header',
            header_name: props.cred.header_name,
            header_value: event.target.value,
        };
        props.setCredential(credential);
    };
    return (
        <>
            <ControlGroup label="Header Name" help="e.g. x-api-key">
                <Text
                    value={props.cred.header_name}
                    autoComplete="off"
                    onChange={handleChangeHeaderName}
                />
            </ControlGroup>
            <ControlGroup label="Header Value" controlsLayout="fillJoin">
                <Text
                    value={props.cred.header_value}
                    passwordVisibilityToggle
                    type="password"
                    autoComplete="off"
                    canClear
                    onChange={handleChangeHeaderValue}
                />
            </ControlGroup>
        </>
    );
}

function HMACForm(props) {
    const handleChangeSecret = (event) => {
        let credential = {
            type: 'hmac',
            hmac_secret: event.target.value,
            hmac_hash_function: props.cred.hmac_hash_function,
            hmac_digest_type: props.cred.hmac_digest_type,
            hmac_sig_header: props.cred.hmac_sig_header,
            hmac_time_header: props.cred.hmac_time_header,
        };
        props.setCredential(credential);
    };

    const handleChangeHashFunction = (event, { value }) => {
        let credential = {
            type: 'hmac',
            hmac_secret: props.cred.hmac_secret,
            hmac_hash_function: value,
            hmac_digest_type: props.cred.hmac_digest_type,
            hmac_sig_header: props.cred.hmac_sig_header,
            hmac_time_header: props.cred.hmac_time_header,
        };
        props.setCredential(credential);
    };

    const handleChangeDigestType = (event, { value }) => {
        let credential = {
            type: 'hmac',
            hmac_secret: props.cred.hmac_secret,
            hmac_hash_function: props.cred.hmac_hash_function,
            hmac_digest_type: value,
            hmac_sig_header: props.cred.hmac_sig_header,
            hmac_time_header: props.cred.hmac_time_header,
        };
        props.setCredential(credential);
    };

    const handleChangeSigHeader = (event) => {
        let credential = {
            type: 'hmac',
            hmac_secret: props.cred.hmac_secret,
            hmac_hash_function: props.cred.hmac_hash_function,
            hmac_digest_type: props.cred.hmac_digest_type,
            hmac_sig_header: event.target.value,
            hmac_time_header: props.cred.hmac_time_header,
        };
        props.setCredential(credential);
    };

    const handleChangeTimeHeader = (event) => {
        let credential = {
            type: 'hmac',
            hmac_secret: props.cred.hmac_secret,
            hmac_hash_function: props.cred.hmac_hash_function,
            hmac_digest_type: props.cred.hmac_digest_type,
            hmac_sig_header: props.cred.hmac_sig_header,
            hmac_time_header: event.target.value,
        };
        props.setCredential(credential);
    };
    return (
        <>
            <ControlGroup
                label="HMAC Secret"
                tooltip="This will be used by the Webhook receiver to verify the request"
            >
                <Text
                    value={props.cred.hmac_secret}
                    passwordVisibilityToggle
                    type="password"
                    autoComplete="off"
                    canClear
                    onChange={handleChangeSecret}
                />
            </ControlGroup>
            <ControlGroup label="Hash Function">
                <Select
                    defaultValue="sha1"
                    value={props.cred.hmac_hash_function}
                    onChange={handleChangeHashFunction}
                >
                    <Select.Option label="SHA1" value="sha1" />
                    <Select.Option label="SHA256" value="sha256" />
                    <Select.Option label="SHA512" value="sha512" />
                </Select>
            </ControlGroup>
            <ControlGroup
                label="Digest Type"
                tooltip="This is how the HMAC signature is encoded in the HTTP header. I usually see this base64-encoded, but I've added an option to send as a hex digest too in case a user needs it."
            >
                <Select value={props.cred.hmac_digest_type} onChange={handleChangeDigestType}>
                    <Select.Option label="Base64" value="b64" />
                    <Select.Option label="Hex digest" value="hex" />
                </Select>
            </ControlGroup>
            <ControlGroup
                label="HMAC Signature Header"
                tooltip="The HTTP header that the HMAC signature will be sent in"
                help="e.g. X-Sign"
            >
                <Text
                    value={props.cred.hmac_sig_header}
                    autoComplete="off"
                    onChange={handleChangeSigHeader}
                />
            </ControlGroup>
            <ControlGroup
                label="HMAC Timestamp Header"
                tooltip="The HTTP header that the HMAC timestamp will be sent in"
                help="Leave this blank to entirely skip using timestamp to compute the HMAC signature. Some services use timestamp, some don't."
            >
                <Text
                    value={props.cred.hmac_time_header}
                    autoComplete="off"
                    onChange={handleChangeTimeHeader}
                />
            </ControlGroup>
        </>
    );
}

function GenericCredForm(props) {
    return (
        <>
            { props.error && 
                <Message appearance="fill" type="error">
                    {props.error}
                </Message>
            }
            {props.type == 'basic' && (
                <HTTPCredForm cred={props.cred} setCredential={props.setCredential} />
            )}
            {props.type == 'header' && (
                <HeaderCredForm cred={props.cred} setCredential={props.setCredential} />
            )}
            {props.type == 'hmac' && (
                <HMACForm cred={props.cred} setCredential={props.setCredential} />
            )}
        </>
    );
}

export default GenericCredForm;
