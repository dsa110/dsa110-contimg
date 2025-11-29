#!/usr/bin/env node
/**
 * Streamlined script to fix remaining TypeScript errors
 * Categorizes errors and applies targeted fixes
 */

import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Get all TypeScript errors
function getAllErrors() {
  try {
    const output = execSync("npx tsc -b 2>&1", {
      encoding: "utf8",
      cwd: path.join(__dirname, ".."),
      stdio: "pipe",
    });

    const errors = output
      .split("\n")
      .filter((line) => line.includes("error TS"))
      .map((line) => {
        const match = line.match(/^([^(]+)\((\d+),(\d+)\): error (TS\d+): (.+)$/);
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
      .filter((line) => line.includes("error TS"))
      .map((line) => {
        const match = line.match(/^([^(]+)\((\d+),(\d+)\): error (TS\d+): (.+)$/);
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

// Categorize errors
function categorizeErrors(errors) {
  const categories = {
    missingExports: [], // TS2724, TS2305
    missingTypes: [], // TS2304, TS18046
    typeMismatches: [], // TS2322, TS2345
    propertyErrors: [], // TS2353, TS2551
    namespaceErrors: [], // TS2503
    conversionErrors: [], // TS2352
    exportErrors: [], // TS2459
    indexErrors: [], // TS2538
    overloadErrors: [], // TS2769
    unusedVars: [], // TS6133
  };

  errors.forEach((err) => {
    if (["TS2724", "TS2305"].includes(err.code)) {
      categories.missingExports.push(err);
    } else if (["TS2304", "TS18046"].includes(err.code)) {
      categories.missingTypes.push(err);
    } else if (["TS2322", "TS2345"].includes(err.code)) {
      categories.typeMismatches.push(err);
    } else if (["TS2353", "TS2551"].includes(err.code)) {
      categories.propertyErrors.push(err);
    } else if (err.code === "TS2503") {
      categories.namespaceErrors.push(err);
    } else if (err.code === "TS2352") {
      categories.conversionErrors.push(err);
    } else if (err.code === "TS2459") {
      categories.exportErrors.push(err);
    } else if (err.code === "TS2538") {
      categories.indexErrors.push(err);
    } else if (err.code === "TS2769") {
      categories.overloadErrors.push(err);
    } else if (err.code === "TS6133") {
      categories.unusedVars.push(err);
    }
  });

  return categories;
}

// Fix missing exports
function fixMissingExports(errors) {
  const fixes = [];

  errors.forEach((err) => {
    if (err.message.includes("DataInstanceList")) {
      // Check if DataInstanceList exists in types.ts
      const typesPath = path.join(__dirname, "..", "src", "api", "types.ts");
      if (fs.existsSync(typesPath)) {
        const content = fs.readFileSync(typesPath, "utf8");
        if (!content.includes("export interface DataInstanceList")) {
          // Add it after DataInstance
          const dataInstanceMatch = content.match(/(export interface DataInstance[^}]+})/s);
          if (dataInstanceMatch) {
            const insertPoint = content.indexOf(dataInstanceMatch[0]) + dataInstanceMatch[0].length;
            const newContent =
              content.slice(0, insertPoint) +
              "\n\nexport interface DataInstanceList {\n  items: DataInstance[];\n  total: number;\n}" +
              content.slice(insertPoint);
            fs.writeFileSync(typesPath, newContent, "utf8");
            fixes.push({ file: "types.ts", action: "Added DataInstanceList interface" });
          }
        }
      }
    } else if (err.message.includes("HealthSummary")) {
      // Similar fix for HealthSummary
      const typesPath = path.join(__dirname, "..", "src", "api", "types.ts");
      if (fs.existsSync(typesPath)) {
        const content = fs.readFileSync(typesPath, "utf8");
        if (
          !content.includes("export interface HealthSummary") &&
          !content.includes("export type HealthSummary")
        ) {
          // Add basic HealthSummary type
          const newContent =
            content +
            "\n\nexport interface HealthSummary {\n  status: string;\n  [key: string]: unknown;\n}\n";
          fs.writeFileSync(typesPath, newContent, "utf8");
          fixes.push({ file: "types.ts", action: "Added HealthSummary interface" });
        }
      }
    }
  });

  return fixes;
}

// Fix missing types
function fixMissingTypes(errors) {
  const fixes = [];

  errors.forEach((err) => {
    if (err.message.includes("PerSPWStats")) {
      const filePath = path.join(__dirname, "..", err.file);
      if (fs.existsSync(filePath)) {
        const content = fs.readFileSync(filePath, "utf8");
        const lines = content.split("\n");

        // Check if PerSPWStats is imported
        if (!content.includes("PerSPWStats") || !content.includes("import.*PerSPWStats")) {
          // Find import statement from types
          const importMatch = content.match(/import\s+.*from\s+['"]\.\.\/api\/types['"]/);
          if (importMatch) {
            const importLine = importMatch[0];
            if (!importLine.includes("PerSPWStats")) {
              // Add PerSPWStats to import
              const newImport = importLine.replace(/(\{[^}]+)\}/, "$1, PerSPWStats}");
              const newContent = content.replace(importLine, newImport);
              fs.writeFileSync(filePath, newContent, "utf8");
              fixes.push({ file: err.file, action: "Added PerSPWStats import" });
            }
          }
        }
      }
    }
  });

  return fixes;
}

// Fix property errors
function fixPropertyErrors(errors) {
  const fixes = [];

  errors.forEach((err) => {
    if (err.message.includes("modified_time") && err.message.includes("modified_at")) {
      // Replace modified_time with modified_at
      const filePath = path.join(__dirname, "..", err.file);
      if (fs.existsSync(filePath)) {
        const content = fs.readFileSync(filePath, "utf8");
        const lines = content.split("\n");
        const lineIndex = err.line - 1;

        if (lineIndex >= 0 && lineIndex < lines.length) {
          const line = lines[lineIndex];
          if (line.includes("modified_time")) {
            lines[lineIndex] = line.replace(/modified_time/g, "modified_at");
            fs.writeFileSync(filePath, lines.join("\n"), "utf8");
            fixes.push({
              file: err.file,
              line: err.line,
              action: "Replaced modified_time with modified_at",
            });
          }
        }
      }
    } else if (err.message.includes("order_by") && err.message.includes("ImageFilters")) {
      // Remove order_by or add to ImageFilters
      const filePath = path.join(__dirname, "..", err.file);
      if (fs.existsSync(filePath)) {
        const content = fs.readFileSync(filePath, "utf8");
        const lines = content.split("\n");
        const lineIndex = err.line - 1;

        if (lineIndex >= 0 && lineIndex < lines.length) {
          const line = lines[lineIndex];
          if (line.includes("order_by")) {
            // Remove the property
            lines[lineIndex] = line.replace(/order_by\s*:\s*[^,}]+[,]?/g, "");
            fs.writeFileSync(filePath, lines.join("\n"), "utf8");
            fixes.push({ file: err.file, line: err.line, action: "Removed order_by property" });
          }
        }
      }
    } else if (err.message.includes("ms_path") && err.message.includes("NotebookGenerateRequest")) {
      // Similar fix for ms_path
      const filePath = path.join(__dirname, "..", err.file);
      if (fs.existsSync(filePath)) {
        const content = fs.readFileSync(filePath, "utf8");
        const lines = content.split("\n");
        const lineIndex = err.line - 1;

        if (lineIndex >= 0 && lineIndex < lines.length) {
          const line = lines[lineIndex];
          if (line.includes("ms_path")) {
            // Try msPath instead
            lines[lineIndex] = line.replace(/ms_path/g, "msPath");
            fs.writeFileSync(filePath, lines.join("\n"), "utf8");
            fixes.push({ file: err.file, line: err.line, action: "Replaced ms_path with msPath" });
          }
        }
      }
    }
  });

  return fixes;
}

// Fix namespace errors (NodeJS)
function fixNamespaceErrors(errors) {
  const fixes = [];

  errors.forEach((err) => {
    if (err.message.includes("NodeJS")) {
      const filePath = path.join(__dirname, "..", err.file);
      if (fs.existsSync(filePath)) {
        const content = fs.readFileSync(filePath, "utf8");

        // Check if @types/node types are referenced in tsconfig
        // For now, add type assertion
        const lines = content.split("\n");
        const lineIndex = err.line - 1;

        if (lineIndex >= 0 && lineIndex < lines.length) {
          const line = lines[lineIndex];
          if (line.includes("NodeJS.")) {
            // Replace NodeJS.Timeout with ReturnType<typeof setTimeout>
            lines[lineIndex] = line.replace(/NodeJS\.Timeout/g, "ReturnType<typeof setTimeout>");
            fs.writeFileSync(filePath, lines.join("\n"), "utf8");
            fixes.push({ file: err.file, line: err.line, action: "Replaced NodeJS.Timeout" });
          }
        }
      }
    }
  });

  return fixes;
}

// Fix conversion errors
function fixConversionErrors(errors) {
  const fixes = [];

  errors.forEach((err) => {
    if (err.message.includes("CARTAMessageType") && err.message.includes("unknown")) {
      const filePath = path.join(__dirname, "..", err.file);
      if (fs.existsSync(filePath)) {
        const content = fs.readFileSync(filePath, "utf8");
        const lines = content.split("\n");
        const lineIndex = err.line - 1;

        if (lineIndex >= 0 && lineIndex < lines.length) {
          const line = lines[lineIndex];
          if (line.includes("as CARTAMessageType")) {
            // Change to double assertion via unknown
            lines[lineIndex] = line.replace(
              /as CARTAMessageType/g,
              "as unknown as CARTAMessageType"
            );
            fs.writeFileSync(filePath, lines.join("\n"), "utf8");
            fixes.push({
              file: err.file,
              line: err.line,
              action: "Fixed CARTAMessageType conversion",
            });
          }
        }
      }
    }
  });

  return fixes;
}

// Main execution
function main() {
  const dryRun = process.argv.includes("--dry-run");
  const verbose = process.argv.includes("--verbose");

  console.log("Analyzing TypeScript errors...\n");
  const errors = getAllErrors();

  if (errors.length === 0) {
    console.log("No TypeScript errors found!");
    return;
  }

  console.log(`Found ${errors.length} TypeScript errors\n`);

  const categories = categorizeErrors(errors);

  console.log("Error breakdown:");
  Object.keys(categories).forEach((cat) => {
    if (categories[cat].length > 0) {
      console.log(`  ${cat}: ${categories[cat].length}`);
    }
  });
  console.log("");

  if (dryRun) {
    console.log("DRY RUN MODE - No files will be modified\n");
    return;
  }

  let totalFixes = 0;

  // Fix missing exports
  if (categories.missingExports.length > 0) {
    console.log("Fixing missing exports...");
    const fixes = fixMissingExports(categories.missingExports);
    totalFixes += fixes.length;
    fixes.forEach((fix) => {
      console.log(`  :check_mark: ${fix.file}: ${fix.action}`);
    });
  }

  // Fix missing types
  if (categories.missingTypes.length > 0) {
    console.log("\nFixing missing types...");
    const fixes = fixMissingTypes(categories.missingTypes);
    totalFixes += fixes.length;
    fixes.forEach((fix) => {
      console.log(`  :check_mark: ${fix.file}: ${fix.action}`);
    });
  }

  // Fix property errors
  if (categories.propertyErrors.length > 0) {
    console.log("\nFixing property errors...");
    const fixes = fixPropertyErrors(categories.propertyErrors);
    totalFixes += fixes.length;
    fixes.forEach((fix) => {
      console.log(`  :check_mark: ${fix.file}:${fix.line}: ${fix.action}`);
    });
  }

  // Fix namespace errors
  if (categories.namespaceErrors.length > 0) {
    console.log("\nFixing namespace errors...");
    const fixes = fixNamespaceErrors(categories.namespaceErrors);
    totalFixes += fixes.length;
    fixes.forEach((fix) => {
      console.log(`  :check_mark: ${fix.file}:${fix.line}: ${fix.action}`);
    });
  }

  // Fix conversion errors
  if (categories.conversionErrors.length > 0) {
    console.log("\nFixing conversion errors...");
    const fixes = fixConversionErrors(categories.conversionErrors);
    totalFixes += fixes.length;
    fixes.forEach((fix) => {
      console.log(`  :check_mark: ${fix.file}:${fix.line}: ${fix.action}`);
    });
  }

  console.log(`\n:check_mark: Applied ${totalFixes} fixes`);
  console.log("\nRemaining errors:");
  console.log(`  - Unused variables (TS6133): ${categories.unusedVars.length} - Run ESLint --fix`);
  console.log(
    `  - Type mismatches (TS2322/TS2345): ${categories.typeMismatches.length} - May need manual fixes`
  );
  console.log(
    `  - Overload errors (TS2769): ${categories.overloadErrors.length} - May need manual fixes`
  );
  console.log(
    `  - Export errors (TS2459): ${categories.exportErrors.length} - May need manual fixes`
  );
  console.log(
    `  - Index errors (TS2538): ${categories.indexErrors.length} - May need manual fixes`
  );
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { getAllErrors, categorizeErrors };
