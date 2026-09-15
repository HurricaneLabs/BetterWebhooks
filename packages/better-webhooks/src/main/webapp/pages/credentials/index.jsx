import React from 'react';

import layout from '@splunk/react-page';
import WebhookCredentials from '@splunk/webhook-credentials';
import { getUserTheme, getThemeOptions } from '@splunk/splunk-utils/themes';

import { StyledContainer, StyledGreeting } from './StartStyles';

getUserTheme()
    .then((theme) => {
        // react-page defaults to enterprise/comfortable; getThemeOptions is Splunk's
        // own mapping, so pass family and density explicitly instead.
        const { family, colorScheme, density } = getThemeOptions(theme);
        layout(
            <StyledContainer>
                <WebhookCredentials />
            </StyledContainer>,
            {
                themeFamily: family,
                theme: colorScheme,
                themeDensity: density,
            }
        );
    })
    .catch((e) => {
        const errorEl = document.createElement('span');
        errorEl.innerHTML = e;
        document.body.appendChild(errorEl);
    });
