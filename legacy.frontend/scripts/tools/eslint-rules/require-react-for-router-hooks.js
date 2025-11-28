/**
 * ESLint rule: require-react-for-router-hooks
 *
 * Requires React import when using react-router-dom hooks that internally use useContext.
 * This prevents "Cannot read properties of null (reading 'useContext')" errors in React 19.
 *
 * React Router hooks (useNavigate, useLocation, useParams, etc.) internally use
 * React's useContext, which requires React to be in scope in React 19.
 */

export default {
  meta: {
    type: "problem",
    docs: {
      description: "Require React import when using react-router-dom hooks",
      recommended: true,
    },
    fixable: null,
    schema: [],
    messages: {
      missingReactImport:
        "React must be imported when using {{hookName}} from react-router-dom. " +
        "React Router hooks internally use useContext, which requires React in scope in React 19. " +
        "Add: import React from 'react'; or import React, { ... } from 'react';",
    },
  },
  create(context) {
    const routerHooks = new Set([
      "useNavigate",
      "useLocation",
      "useParams",
      "useSearchParams",
      "useRouter",
      "useNavigationType",
      "useOutlet",
      "useOutletContext",
      "useResolvedPath",
      "useRoutes",
      "useHref",
      "useLinkClickHandler",
      "useFetcher",
      "useFetchers",
      "useFormAction",
      "useFormMethod",
      "useLoaderData",
      "useActionData",
      "useRevalidator",
      "useSubmit",
      "useNavigation",
      "useRouteLoaderData",
      "useMatches",
      "useMatch",
    ]);

    let hasReactImport = false;
    let hasRouterImport = false;
    let routerHookUsed = null;
    let importNode = null;

    return {
      Program(node) {
        // Reset state for each file
        hasReactImport = false;
        hasRouterImport = false;
        routerHookUsed = null;
        importNode = null;
      },

      ImportDeclaration(node) {
        // Check for React import
        if (node.source.value === "react") {
          // Check if it's a default import or namespace import
          const hasDefaultImport = node.specifiers.some(
            (spec) => spec.type === "ImportDefaultSpecifier"
          );
          const hasNamespaceImport = node.specifiers.some(
            (spec) => spec.type === "ImportNamespaceSpecifier"
          );
          if (hasDefaultImport || hasNamespaceImport) {
            hasReactImport = true;
          }
        }

        // Check for react-router-dom import
        if (node.source.value === "react-router-dom") {
          hasRouterImport = true;
          importNode = node;
        }
      },

      CallExpression(node) {
        // Check if a router hook is being called
        if (node.callee.type === "Identifier" && routerHooks.has(node.callee.name)) {
          routerHookUsed = node.callee.name;
        }
      },

      "Program:exit"(node) {
        // If react-router-dom hooks are used but React is not imported, report error
        if (hasRouterImport && routerHookUsed && !hasReactImport) {
          context.report({
            node: importNode || node,
            messageId: "missingReactImport",
            data: {
              hookName: routerHookUsed,
            },
          });
        }
      },
    };
  },
};
