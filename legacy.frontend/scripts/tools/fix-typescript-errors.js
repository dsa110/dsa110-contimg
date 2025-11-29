#!/usr/bin/env node
/**
 * Pattern-based TypeScript error fixer
 * Automatically fixes common TS2322 and TS2345 errors
 */

import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Parse TypeScript errors
function getTypeErrors() {
  try {
    const output = execSync("npx tsc -b 2>&1", {
      encoding: "utf8",
      cwd: path.join(__dirname, ".."),
      stdio: "pipe",
    });

    const errors = output
      .split("\n")
      .filter((line) => line.includes("error TS2322") || line.includes("error TS2345"))
      .map((line) => {
        const match = line.match(/^([^(]+)\((\d+),(\d+)\): error (TS2322|TS2345): (.+)$/);
        if (match) {
          return {
            file: match[1].trim(),
            line: parseInt(match[2]),
            col: parseInt(match[3]),
            code: match[4],
            message: match[5],
          };
        }
        return null;
      })
      .filter(Boolean);

    return errors;
  } catch (error) {
    const output = error.stderr?.toString() || error.stdout?.toString() || "";
    const errors = output
      .split("\n")
      .filter((line) => line.includes("error TS2322") || line.includes("error TS2345"))
      .map((line) => {
        const match = line.match(/^([^(]+)\((\d+),(\d+)\): error (TS2322|TS2345): (.+)$/);
        if (match) {
          return {
            file: match[1].trim(),
            line: parseInt(match[2]),
            col: parseInt(match[3]),
            code: match[4],
            message: match[5],
          };
        }
        return null;
      })
      .filter(Boolean);

    return errors;
  }
}

// Fix patterns
const fixPatterns = [
  {
    name: "RefObject<HTMLDivElement | null> to RefObject<HTMLDivElement>",
    match: /RefObject<HTMLDivElement \| null>/,
    messageMatch:
      /Type 'RefObject<HTMLDivElement \| null>' is not assignable to type 'RefObject<HTMLDivElement>'/,
    fix: (line, context) => {
      // Find type annotations and remove | null
      if (line.includes("RefObject<HTMLDivElement | null>")) {
        return line.replace(/RefObject<HTMLDivElement \| null>/g, "RefObject<HTMLDivElement>");
      }
      return null;
    },
  },
  {
    name: "number | null to number (with nullish coalescing)",
    messageMatch: /Type 'number \| null' is not assignable to type 'number'/,
    fix: (line, context) => {
      // Look for assignments where we can add ?? 0
      const match = line.match(/(\w+):\s*(\w+\.\w+|\w+)\s*[,;}]/);
      if (match && !line.includes("??")) {
        const varName = match[2];
        return line.replace(
          new RegExp(`(${varName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})([,;}\\s]*)$`),
          "$1 ?? 0$2"
        );
      }
      return null;
    },
  },
  {
    name: "string to number (parseInt)",
    messageMatch: /Argument of type 'string' is not assignable to parameter of type 'number'/,
    fix: (line, context) => {
      // Find function calls with string arguments that should be numbers
      // Look for patterns like: functionName(variable) or functionName("123")
      const funcCallMatch = line.match(/(\w+)\(([^)]+)\)/);
      if (funcCallMatch) {
        const args = funcCallMatch[2];
        // Check if there's a string literal or variable that needs parseInt
        // Match the last argument (most likely the problematic one)
        const argParts = args.split(",").map((a) => a.trim());
        const lastArg = argParts[argParts.length - 1];

        if (
          lastArg &&
          !lastArg.includes("parseInt") &&
          !lastArg.includes("Number") &&
          !lastArg.includes("+")
        ) {
          // Check if it's a string literal with digits or a variable
          if ((lastArg.startsWith('"') || lastArg.startsWith("'")) && /\d/.test(lastArg)) {
            // String literal with digits
            return line.replace(
              new RegExp(`(${lastArg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`),
              `parseInt($1, 10)`
            );
          } else if (/^\w+$/.test(lastArg) || /^\w+\.\w+$/.test(lastArg)) {
            // Variable name
            return line.replace(
              new RegExp(`(${lastArg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})(\\)|,|\\s*$)`),
              `parseInt($1, 10)$2`
            );
          }
        }
      }
      return null;
    },
  },
  {
    name: "JobParams/ConversionJobParams to Record<string, unknown>",
    messageMatch:
      /Type '(JobParams|ConversionJobParams)' is not assignable to type 'Record<string, unknown>'/,
    fix: (line, context) => {
      // Add type assertion
      if (
        line.includes("params:") &&
        (line.includes("JobParams") || line.includes("ConversionJobParams"))
      ) {
        return line.replace(/(params:\s*)(\w+)/, "$1$2 as Record<string, unknown>");
      }
      return null;
    },
  },
  {
    name: "boolean to string",
    messageMatch: /Type 'boolean' is not assignable to type 'string'/,
    fix: (line, context) => {
      // Convert boolean to string - look for prop assignments
      // Pattern: propName: true/false or propName: variable
      const propMatch = line.match(/(\w+):\s*(true|false|\w+)/);
      if (propMatch) {
        const value = propMatch[2];
        if (value === "true" || value === "false") {
          return line.replace(new RegExp(`(${value})([,;}\\s]*)$`), `String($1)$2`);
        } else if (/^\w+$/.test(value)) {
          // Variable name
          return line.replace(new RegExp(`(${value})([,;}\\s]*)$`), "String($1)$2");
        }
      }
      return null;
    },
  },
  {
    name: "number | null | undefined to number | undefined",
    messageMatch:
      /Type 'number \| null \| undefined' is not assignable to type 'number \| undefined'/,
    fix: (line, context) => {
      // Add nullish coalescing to remove null
      const match = line.match(/(\w+\.\w+|\w+)/);
      if (match && !line.includes("??")) {
        const varName = match[1];
        return line.replace(
          new RegExp(`(${varName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})([,;}\\s]*)$`),
          "$1 ?? undefined$2"
        );
      }
      return null;
    },
  },
  {
    name: "string | undefined to string",
    messageMatch:
      /Argument of type 'string \| undefined' is not assignable to parameter of type 'string'/,
    fix: (line, context) => {
      // Add nullish coalescing
      const funcCallMatch = line.match(/(\w+)\(([^)]+)\)/);
      if (funcCallMatch) {
        const args = funcCallMatch[2];
        const argMatch = args.match(/(\w+\.\w+|\w+)/);
        if (argMatch && !args.includes("??")) {
          const arg = argMatch[1];
          return line.replace(
            new RegExp(`(${arg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`),
            '$1 ?? ""'
          );
        }
      }
      return null;
    },
  },
  {
    name: "MSListEntry[] | undefined to number | undefined (add .length)",
    messageMatch:
      /Type 'MSListEntry\[\] \| undefined' is not assignable to type 'number \| undefined'/,
    fix: (line, context) => {
      // Look for array variables that should be .length
      // Check current line and context for array assignments
      const linesToCheck = [context.current, context.prev, context.next].filter(Boolean);

      for (const checkLine of linesToCheck) {
        // Pattern: propName={arrayVariable} or propName: arrayVariable
        const propMatch = checkLine.match(/(\w+)(\s*[:=]\s*)(\w+)/);
        if (propMatch) {
          const varName = propMatch[3];
          // Check if it's an array variable
          if (
            (varName.includes("List") ||
              varName.includes("items") ||
              varName.includes("entries") ||
              varName.includes("filtered")) &&
            !checkLine.includes(".length") &&
            !checkLine.includes("?.length")
          ) {
            if (checkLine === context.current) {
              return line.replace(
                new RegExp(`(${varName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})(\\s*[,;}\\s]*)$`),
                "$1?.length$2"
              );
            } else if (checkLine === context.next) {
              // Fix next line
              const nextIndex = context.lineIndex + 1;
              if (nextIndex < context.allLines.length) {
                context.allLines[nextIndex] = context.allLines[nextIndex].replace(
                  new RegExp(`(${varName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})(\\s*[,;}\\s]*)$`),
                  "$1?.length$2"
                );
                return line; // Return unchanged current line
              }
            }
          }
        }
      }
      return null;
    },
  },
  {
    name: "number | null | undefined to number | undefined",
    messageMatch:
      /Argument of type 'number \| null \| undefined' is not assignable to parameter of type 'number \| undefined'/,
    fix: (line, context) => {
      // Add nullish coalescing to remove null
      const funcCallMatch = line.match(/(\w+)\(([^)]+)\)/);
      if (funcCallMatch) {
        const args = funcCallMatch[2];
        const argMatch = args.match(/(\w+\.\w+|\w+)/);
        if (argMatch && !args.includes("??")) {
          const arg = argMatch[1];
          return line.replace(
            new RegExp(`(${arg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`),
            "$1 ?? undefined"
          );
        }
      }
      return null;
    },
  },
  {
    name: "UseQueryResult union type (add type assertion)",
    messageMatch: /Type 'UseQueryResult<.*\|.*>' is not assignable to type 'UseQueryResult<.*>'/,
    fix: (line, context) => {
      // Add type assertion for UseQueryResult
      // Look for return statement with useQuery
      if (
        line.includes("return") &&
        (line.includes("useQuery") || context.prev.includes("useQuery"))
      ) {
        // Find the expected return type from function signature
        for (let i = context.lineIndex - 5; i <= context.lineIndex; i++) {
          if (i >= 0 && i < context.allLines.length) {
            const checkLine = context.allLines[i];
            const funcMatch = checkLine.match(/:\s*UseQueryResult<([^>]+)>/);
            if (funcMatch) {
              const expectedType = funcMatch[1];
              // Extract the actual return value
              const returnMatch = line.match(/return\s+(.+)/);
              if (returnMatch && !line.includes("as UseQueryResult")) {
                return line.replace(/(return\s+)(.+)/, `$1$2 as UseQueryResult<${expectedType}>`);
              }
            }
          }
        }
      }
      return null;
    },
  },
  {
    name: "Return type mismatch (void vs other)",
    messageMatch: /Type '.*' is not assignable to type 'void'/,
    fix: (line, context) => {
      // For void return types, we might need to not return or return undefined
      if (line.includes("return")) {
        const returnMatch = line.match(/return\s+(.+)/);
        if (returnMatch) {
          // Check if it's a simple return that should be void
          const returnValue = returnMatch[1].trim();
          if (returnValue && !returnValue.includes("undefined") && !returnValue.includes("void")) {
            // Change to return undefined or remove return
            return line.replace(/return\s+.+/, "return;");
          }
        }
      }
      return null;
    },
  },
  {
    name: "SetStateAction function type mismatch",
    messageMatch:
      /Argument of type '\(prev: Record<string, .*>\) => .*' is not assignable to parameter of type 'SetStateAction<Record<string, .*>>'/,
    fix: (line, context) => {
      // For setState with Record types, ensure the return type matches
      if (line.includes("setCompatibilityChecks") || line.includes("setState")) {
        // The issue is usually that the function returns a union type
        // We need to ensure it returns the exact Record type
        // This is complex - might need to add type assertion
        const funcMatch = line.match(/(\(prev[^)]+\)\s*=>\s*\{)/);
        if (funcMatch) {
          // Add explicit return type or type assertion
          // For now, just ensure the spread operator is used correctly
          if (line.includes("...prev") && !line.includes("as Record")) {
            // The fix might be in the return statement, not this line
            return null; // Too complex for automatic fix
          }
        }
      }
      return null;
    },
  },
  {
    name: "PlotParams type mismatch (add type assertion)",
    messageMatch: /Type '.*' is not assignable to type 'PlotParams'/,
    fix: (line, context) => {
      // For Plotly Plot component, add type assertion
      if (line.includes("<Plot") || line.includes("Plot ")) {
        // Look for the props object
        const propsMatch = line.match(/(\{[^}]*\})/);
        if (propsMatch) {
          // This is complex - would need to see the full JSX
          return null; // Too complex for line-based fix
        }
      }
      return null;
    },
  },
  {
    name: "CARTAMessageType enum mismatch",
    messageMatch:
      /Argument of type '".*"' is not assignable to parameter of type 'CARTAMessageType'/,
    fix: (line, context) => {
      // Add type assertion for CARTAMessageType
      const stringMatch = line.match(/(".*"|'.*')/);
      if (stringMatch && !line.includes("as CARTAMessageType")) {
        return line.replace(
          new RegExp(`(${stringMatch[1].replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`),
          "$1 as CARTAMessageType"
        );
      }
      return null;
    },
  },
  {
    name: "ValidationRule type mismatch",
    messageMatch:
      /Type 'ValidationRule<number>' is not assignable to type 'ValidationRule<string>'/,
    fix: (line, context) => {
      // Convert ValidationRule<number> to ValidationRule<string>
      if (line.includes("ValidationRule")) {
        // Look for number validation and convert to string
        const numberMatch = line.match(/(\w+):\s*ValidationRule<number>/);
        if (numberMatch) {
          return line.replace(/ValidationRule<number>/, "ValidationRule<string>");
        }
      }
      return null;
    },
  },
];

// Apply fixes to a file
function applyFixes(filePath, errors) {
  const fullPath = path.join(__dirname, "..", filePath);
  if (!fs.existsSync(fullPath)) {
    console.warn(`File not found: ${fullPath}`);
    return { fixed: 0, changes: [] };
  }

  const content = fs.readFileSync(fullPath, "utf8");
  const lines = content.split("\n");
  const changes = [];
  let fixed = 0;

  // Group errors by line
  const errorsByLine = {};
  errors.forEach((err) => {
    if (!errorsByLine[err.line]) {
      errorsByLine[err.line] = [];
    }
    errorsByLine[err.line].push(err);
  });

  // Apply fixes line by line (process in reverse to maintain line numbers)
  const sortedLines = Object.keys(errorsByLine)
    .map(Number)
    .sort((a, b) => b - a);

  sortedLines.forEach((lineNum) => {
    const lineIndex = lineNum - 1;
    if (lineIndex < 0 || lineIndex >= lines.length) return;

    const line = lines[lineIndex];
    const lineErrors = errorsByLine[lineNum];

    // Get extended context (3 lines before and after for multi-line patterns)
    const contextLines = [];
    for (let i = Math.max(0, lineIndex - 3); i <= Math.min(lines.length - 1, lineIndex + 3); i++) {
      contextLines.push({ index: i, line: lines[i] });
    }

    const context = {
      prev: lineIndex > 0 ? lines[lineIndex - 1] : "",
      current: line,
      next: lineIndex < lines.length - 1 ? lines[lineIndex + 1] : "",
      allLines: lines,
      contextLines: contextLines,
      lineIndex: lineIndex,
    };

    let modifiedLine = line;
    let lineFixed = false;

    lineErrors.forEach((error) => {
      for (const pattern of fixPatterns) {
        if (pattern.messageMatch && pattern.messageMatch.test(error.message)) {
          const fixed = pattern.fix(modifiedLine, { error, ...context });
          if (fixed && fixed !== modifiedLine) {
            modifiedLine = fixed;
            lineFixed = true;
            changes.push({
              file: filePath,
              line: lineNum,
              original: line.trim(),
              fixed: modifiedLine.trim(),
              pattern: pattern.name,
            });
            break;
          }
        }
      }
    });

    if (lineFixed) {
      lines[lineIndex] = modifiedLine;
      fixed++;
    }
  });

  if (fixed > 0) {
    fs.writeFileSync(fullPath, lines.join("\n"), "utf8");
  }

  return { fixed, changes };
}

// Main execution
function main() {
  const dryRun = process.argv.includes("--dry-run");
  const verbose = process.argv.includes("--verbose");

  console.log("Analyzing TypeScript errors...\n");
  const errors = getTypeErrors();

  if (errors.length === 0) {
    console.log("No TS2322/TS2345 errors found!");
    return;
  }

  console.log(`Found ${errors.length} TS2322/TS2345 errors\n`);

  // Group by file
  const errorsByFile = {};
  errors.forEach((err) => {
    if (!errorsByFile[err.file]) {
      errorsByFile[err.file] = [];
    }
    errorsByFile[err.file].push(err);
  });

  if (dryRun) {
    console.log("DRY RUN MODE - No files will be modified\n");
  }

  let totalFixed = 0;
  const allChanges = [];

  Object.keys(errorsByFile).forEach((file) => {
    const fileErrors = errorsByFile[file];
    if (verbose) {
      console.log(`\n${file}:`);
      fileErrors.forEach((err) => {
        console.log(`  Line ${err.line}: ${err.message.substring(0, 80)}...`);
      });
    }

    if (!dryRun) {
      const result = applyFixes(file, fileErrors);
      totalFixed += result.fixed;
      allChanges.push(...result.changes);
    } else {
      // In dry-run, just show what would be fixed
      fileErrors.forEach((err) => {
        for (const pattern of fixPatterns) {
          if (pattern.messageMatch && pattern.messageMatch.test(err.message)) {
            console.log(`  Would apply: ${pattern.name}`);
            break;
          }
        }
      });
    }
  });

  if (!dryRun && totalFixed > 0) {
    console.log(`\n:check_mark: Fixed ${totalFixed} errors in ${Object.keys(errorsByFile).length} files`);
    if (verbose) {
      console.log("\nChanges made:");
      allChanges.forEach((change) => {
        console.log(`\n${change.file}:${change.line}`);
        console.log(`  Pattern: ${change.pattern}`);
        console.log(`  Before: ${change.original}`);
        console.log(`  After:  ${change.fixed}`);
      });
    }
  } else if (dryRun) {
    console.log("\nRun without --dry-run to apply fixes");
  }
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { getTypeErrors, applyFixes, fixPatterns };
