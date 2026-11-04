import React from 'react';
import PropTypes from 'prop-types';
import ExclamationSquare from '@splunk/react-icons/ExclamationSquare';
import ArrowsCircularDouble from '@splunk/react-icons/ArrowsCircularDouble';
import P from '@splunk/react-ui/Paragraph';

const StatusMessage = ({ error, loaded, credentialsCount }) => {
    if (error) {
        return (
            <>
                <br />
                <P>
                    <ExclamationSquare style={{ color: 'red' }} /> {error}
                </P>
            </>
        );
    }

    if (!loaded) {
        return (
            <>
                <br />
                <P>
                    <ArrowsCircularDouble /> Loading credentials...
                </P>
            </>
        );
    }

    if (credentialsCount === 0) {
        return (
            <>
                <br />
                <P>
                    <ExclamationSquare /> No credentials found. Add one by clicking &quot;New
                    Credential&quot;.
                </P>
            </>
        );
    }

    return null;
};

StatusMessage.propTypes = {
    error: PropTypes.string,
    loaded: PropTypes.bool.isRequired,
    credentialsCount: PropTypes.number.isRequired,
};

export default StatusMessage;
