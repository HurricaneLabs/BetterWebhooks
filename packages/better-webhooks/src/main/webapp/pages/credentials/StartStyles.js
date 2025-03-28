import styled from 'styled-components';
import { variables, mixins } from '@splunk/themes';

const StyledContainer = styled.div`
    ${mixins.reset('inline-block')};
    display: block;
    font-size: ${variables.fontSizeLarge};
    line-height: 200%;
    margin: 20px;
    background-color: ${variables.backgroundColor};
`;

const StyledGreeting = styled.div`
    font-weight: bold;
    color: ${variables.infoColor};
    font-size: ${variables.fontSizeXXLarge};
`;

export { StyledContainer, StyledGreeting };
