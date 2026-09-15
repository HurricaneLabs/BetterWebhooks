import React from 'react';

import layout from '@splunk/react-page';
import WebhookCredentials from '@splunk/webhook-credentials';
import { getUserTheme, getThemeOptions } from '@splunk/splunk-utils/themes';

import { StyledContainer, StyledGreeting } from './StartStyles';

getUserTheme()
    .then((theme) => {
        // react-page defaults to enterprise/comfortable; getThemeOptions is Splunk's
        // own mapping, so pass family and density explicitly instead.
        //
        // Passing themeFamily also makes prisma reachable for the first time, and our
        // styles still use enterprise-era tokens (spacing, spacingHalf, backgroundColor,
        // plus infoColor via the currently-unrendered StyledGreeting) that resolve to
        // undefined under prisma. Not live today: core is documented to bound
        // getUserTheme() by app.conf [ui] supported_themes, and we declare light,dark.
        // Migrate those tokens to pick({enterprise, prisma}) before that ever changes.
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
