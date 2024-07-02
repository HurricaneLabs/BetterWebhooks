import styled from 'styled-components';
import { variables, mixins } from '@splunk/themes';

const StyledContainer = styled.div`
    ${mixins.reset('block')};
    max-width: 1000px;
    min-height: 600px;
    font-size: ${variables.fontSizeLarge};
    line-height: 100%;
    margin: ${variables.spacing} ${variables.spacingHalf};
    padding: ${variables.spacing} ${variables.spacingXXLarge};
    border-radius: ${variables.borderRadius};
    box-shadow: ${variables.overlayShadow};
    background-color: ${variables.backgroundColor};
`;

const StyledHeader = styled.div`
    margin-top: 30px;
    font-weight: bold;
    font-size: 36px;

`;

const AlignRight = styled.div`
    float: right;
`;

const DescriptionText = styled.p`
    max-width: 600px;
`
export { StyledContainer, AlignRight, StyledHeader, DescriptionText};
