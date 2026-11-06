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
`;

// react-ui 5's Modal is a flex column that scrolls only a Modal.Body that is its direct
// child. Our modals wrap Header, Body and Footer in a form, so the form has to be a flex
// column too, and min-height: 0 lets it shrink to fit a short window.
const ModalForm = styled.form`
    display: flex;
    flex-direction: column;
    min-height: 0;
`;
export { StyledContainer, AlignRight, StyledHeader, DescriptionText, ModalForm };
