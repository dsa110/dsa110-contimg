#!/usr/bin/env node
/**
 * Script to automatically remove unused imports and variables
 * based on TypeScript compiler errors (TS6133)
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Get TypeScript errors for unused variables
function getUnusedVariableErrors() {
  try {
    const output = execSync('npx tsc -b 2>&1', { 
      encoding: 'utf8',
      cwd: path.join(__dirname, '..'),
      stdio: 'pipe'
    });
    
    const errors = output
      .split('\n')
      .filter(line => line.includes('error TS6133'))
      .map(line => {
        const match = line.match(/^([^(]+)\((\d+),(\d+)\): error TS6133: '([^']+)'/);
        if (match) {
          return {
            file: match[1].trim(),
            line: parseInt(match[2]),
            col: parseInt(match[3]),
            name: match[4]
          };
        }
        return null;
      })
      .filter(Boolean);
    
    return errors;
  } catch (error) {
    // TypeScript errors are expected, extract from stderr
    const output = error.stderr?.toString() || error.stdout?.toString() || '';
    const errors = output
      .split('\n')
      .filter(line => line.includes('error TS6133'))
      .map(line => {
        const match = line.match(/^([^(]+)\((\d+),(\d+)\): error TS6133: '([^']+)'/);
        if (match) {
          return {
            file: match[1].trim(),
            line: parseInt(match[2]),
            col: parseInt(match[3]),
            name: match[4]
          };
        }
        return null;
      })
      .filter(Boolean);
    
    return errors;
  }
}

// Remove unused import or variable
function removeUnusedItem(filePath, lineNum, name) {
  const fullPath = path.join(__dirname, '..', filePath);
  if (!fs.existsSync(fullPath)) {
    console.warn(`File not found: ${fullPath}`);
    return false;
  }
  
  const content = fs.readFileSync(fullPath, 'utf8');
  const lines = content.split('\n');
  
  if (lineNum < 1 || lineNum > lines.length) {
    console.warn(`Line ${lineNum} out of range in ${filePath}`);
    return false;
  }
  
  const line = lines[lineNum - 1];
  
  // Check if it's an import statement
  if (line.includes('import')) {
    // Try to remove the specific import from the import statement
    const importMatch = line.match(/import\s+(?:\{([^}]+)\}|([^,]+))\s+from/);
    if (importMatch) {
      // This is complex - for now, just log it
      console.log(`Would remove import '${name}' from line ${lineNum} in ${filePath}`);
      console.log(`  Line: ${line.trim()}`);
      return false; // Manual fix needed
    }
  }
  
  // For variable declarations, we could comment them out or remove them
  // But this is risky without understanding context
  console.log(`Would remove variable '${name}' from line ${lineNum} in ${filePath}`);
  console.log(`  Line: ${line.trim()}`);
  
  return false; // Manual fix needed for safety
}

// Main execution
console.log('Analyzing unused variables...\n');
const errors = getUnusedVariableErrors();

console.log(`Found ${errors.length} unused variable errors\n`);

// Group by file
const byFile = {};
errors.forEach(error => {
  if (!byFile[error.file]) {
    byFile[error.file] = [];
  }
  byFile[error.file].push(error);
});

// Show summary
Object.keys(byFile).forEach(file => {
  console.log(`${file}: ${byFile[file].length} unused items`);
  byFile[file].forEach(err => {
    console.log(`  Line ${err.line}: ${err.name}`);
  });
  console.log('');
});

console.log('\nNote: This script identifies unused items but requires manual review.');
console.log('Use ESLint --fix for automatic import removal where possible.');

