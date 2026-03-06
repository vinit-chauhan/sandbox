import "@testing-library/jest-dom";

// jsdom does not implement scrollIntoView; mock it for components that use it
Element.prototype.scrollIntoView = () => {};
