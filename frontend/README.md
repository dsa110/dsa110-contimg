# Frontend Project Documentation

## Overview

This project is a frontend application designed to handle and display provenance
information and error responses in a user-friendly manner. It utilizes React and
TypeScript to create reusable components and hooks that manage state and data
effectively.

## Project Structure

The project is organized into several directories:

- **src**: Contains the main source code for the application.

  - **components**: Contains reusable React components for displaying provenance
    information and error messages.
    - **provenance**: Components related to provenance data.
    - **errors**: Components for displaying error messages and handling error
      states.
  - **hooks**: Custom hooks for managing application state and data retrieval.
  - **utils**: Utility functions for common tasks such as error mapping and
    coordinate formatting.
  - **types**: TypeScript types and interfaces used throughout the application.
  - **constants**: Constants used for error mappings and other fixed values.
  - **api**: API client and error interceptor for handling HTTP requests.

- **legacy**: Contains documentation or notes related to legacy code that has
  been displaced.

- **package.json**: Configuration file for npm, listing dependencies and
  scripts.

- **tsconfig.json**: TypeScript configuration file specifying compiler options.

- **vite.config.ts**: Configuration file for Vite, specifying build and
  development settings.

## Getting Started

To get started with the project, follow these steps:

1. **Clone the repository**:

   ```
   git clone <repository-url>
   cd frontend
   ```

2. **Install dependencies**:

   ```
   npm install
   ```

3. **Run the development server**:

   ```
   npm run dev
   ```

4. **Build the project**:

   ```
   npm run build
   ```

5. **Run Storybook** (component development):
   ```
   npm run storybook
   ```
   See the [Storybook Guide](../docs/STORYBOOK.md) for detailed documentation on
   developing components with Storybook.

## Components

### Provenance Components

- **ProvenanceStrip**: Displays a compact strip showing provenance information.
- **ProvenanceBadge**: Displays a badge indicating the quality assessment (QA)
  grade.
- **ProvenanceLink**: Renders a link to the QA report or other relevant URLs.

### Error Components

- **ErrorDisplay**: Presents a normalized error response to the user.
- **ErrorDetailsExpander**: Allows users to expand and view detailed error
  information.
- **ErrorActionHint**: Provides actionable hints based on the displayed error.

## Hooks

- **useErrorHandler**: Manages error states and provides functions to handle
  errors.
- **useProvenance**: Retrieves and manages provenance data.
- **useErrorMapping**: Maps error codes to user-friendly messages and actions.

## Utilities

- **errorCodes**: Constants representing various error codes.
- **errorMapper**: Maps error responses to user-friendly messages.
- **coordinateFormatter**: Utility functions for formatting coordinates.
- **relativeTime**: Converts timestamps to relative time strings.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for
discussion.

## License

This project is licensed under the MIT License. See the LICENSE file for
details.
