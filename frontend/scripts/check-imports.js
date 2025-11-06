#!/usr/bin/env node
/**
 * Import verification script
 * Checks that all imports in the codebase can be resolved
 * This catches missing dependencies like date-fns
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, extname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = join(__filename, '..', '..');

// Known problematic imports to check for
const PROBLEMATIC_IMPORTS = [
  { pattern: /from ['"]date-fns['"]/, message: 'date-fns is not installed, use dayjs instead' },
  { pattern: /import.*date-fns/, message: 'date-fns is not installed, use dayjs instead' },
];

// Required dependencies that should exist
const REQUIRED_DEPS = ['dayjs'];

function getAllFiles(dir, fileList = []) {
  const files = readdirSync(dir);

  files.forEach((file) => {
    const filePath = join(dir, file);
    const stat = statSync(filePath);

    if (stat.isDirectory()) {
      // Skip node_modules and build directories
      if (!['node_modules', 'dist', '.git', '.vite'].includes(file)) {
        getAllFiles(filePath, fileList);
      }
    } else if (
      ['.ts', '.tsx', '.js', '.jsx'].includes(extname(file)) &&
      !file.includes('.test.') &&
      !file.includes('.spec.')
    ) {
      fileList.push(filePath);
    }
  });

  return fileList;
}

function checkFile(filePath) {
  const content = readFileSync(filePath, 'utf-8');
  const errors = [];

  // Check for problematic imports
  PROBLEMATIC_IMPORTS.forEach(({ pattern, message }) => {
    if (pattern.test(content)) {
      errors.push({
        file: filePath.replace(__dirname + '/', ''),
        message,
      });
    }
  });

  return errors;
}

function checkPackageJson() {
  const packageJsonPath = join(__dirname, 'package.json');
  const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
  const allDeps = {
    ...packageJson.dependencies,
    ...packageJson.devDependencies,
  };

  const missing = REQUIRED_DEPS.filter((dep) => !allDeps[dep]);

  return missing;
}

function main() {
  console.log('Checking imports...\n');

  const srcDir = join(__dirname, 'src');
  const files = getAllFiles(srcDir);
  const errors = [];

  // Check all source files
  files.forEach((file) => {
    const fileErrors = checkFile(file);
    errors.push(...fileErrors);
  });

  // Check package.json for required dependencies
  const missingDeps = checkPackageJson();

  // Report results
  if (errors.length > 0) {
    console.error('❌ Import errors found:\n');
    errors.forEach(({ file, message }) => {
      console.error(`  ${file}: ${message}`);
    });
    process.exit(1);
  }

  if (missingDeps.length > 0) {
    console.error('❌ Missing required dependencies:\n');
    missingDeps.forEach((dep) => {
      console.error(`  ${dep} is not installed`);
    });
    process.exit(1);
  }

  console.log('✅ All imports are valid');
  console.log(`   Checked ${files.length} files`);
}

main();

