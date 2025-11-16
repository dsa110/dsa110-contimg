#!/usr/bin/env node
/**
 * Fix TS6133 errors by prefixing unused variables with underscore
 */

import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function getTypeErrors() {
  try {
    const output = execSync("npx tsc -b 2>&1", {
      cwd: path.join(__dirname, ".."),
      encoding: "utf-8",
    });
    return output;
  } catch (error) {
    return error.stdout || "";
  }
}

function parseError(errorLine) {
  const match = errorLine.match(
    /src\/(.+?)\((\d+),(\d+)\): error TS6133: '(\w+)' is declared but its value is never read/
  );
  if (!match) return null;
  return {
    file: match[1],
    line: parseInt(match[2], 10),
    col: parseInt(match[3], 10),
    varName: match[4],
  };
}

function main() {
  console.log("Finding TS6133 errors (unused variables)...");
  const output = getTypeErrors();
  const errorLines = output.split("\n").filter((line) => line.includes("error TS6133"));

  const errors = errorLines.map(parseError).filter(Boolean);
  console.log(`Found ${errors.length} unused variable errors`);

  const filesToFix = new Map();

  for (const error of errors) {
    const filePath = path.join(__dirname, "..", "src", error.file);
    if (!filesToFix.has(filePath)) {
      filesToFix.set(filePath, []);
    }
    filesToFix.get(filePath).push(error);
  }

  let totalFixed = 0;
  for (const [filePath, fileErrors] of filesToFix) {
    // Sort errors by line number (descending) to maintain line numbers
    fileErrors.sort((a, b) => b.line - a.line);

    let content = fs.readFileSync(filePath, "utf-8");
    let lines = content.split("\n");
    let fileFixed = 0;

    for (const error of fileErrors) {
      const line = lines[error.line - 1];
      if (!line) continue;

      // Skip if already prefixed with underscore
      if (error.varName.startsWith("_")) continue;

      // Skip React hooks
      if (error.varName.startsWith("use")) continue;

      // Replace variable name with prefixed version
      let newLine = line;

      // Check if it's a destructuring pattern
      if (line.includes("const") && line.includes("{") && line.includes("}")) {
        // Destructuring: const { varName } = ...
        newLine = line.replace(
          new RegExp(`(\\{[^}]*?)\\b${error.varName}\\b([^}]*?\\})`, "g"),
          `$1_${error.varName}$2`
        );
      } else if (line.match(/(const|let|var)\s+/)) {
        // Regular declaration: const varName = ...
        newLine = line.replace(
          new RegExp(`(const|let|var)\\s+\\b${error.varName}\\b`, "g"),
          `$1 _${error.varName}`
        );
      } else if (line.match(/\([^)]*\)/)) {
        // Function parameter
        newLine = line.replace(new RegExp(`\\b${error.varName}\\b`, "g"), `_${error.varName}`);
      }

      if (newLine !== line) {
        lines[error.line - 1] = newLine;
        fileFixed++;
        totalFixed++;
      }
    }

    if (fileFixed > 0) {
      fs.writeFileSync(filePath, lines.join("\n"), "utf-8");
      const relativePath = path.relative(path.join(__dirname, "..", "src"), filePath);
      console.log(`Fixed ${fileFixed} error(s) in ${relativePath}`);
    }
  }

  console.log(`\nTotal fixed: ${totalFixed} error(s)`);

  // Check remaining
  const newOutput = getTypeErrors();
  const newErrorLines = newOutput.split("\n").filter((line) => line.includes("error TS6133"));
  console.log(`Remaining TS6133 errors: ${newErrorLines.length}`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
