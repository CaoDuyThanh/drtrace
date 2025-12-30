#!/usr/bin/env node

/**
 * Copy all files from agents/ directory to package agents/ directory
 * This script runs before build to prepare agent files.
 */

const fs = require('fs');
const path = require('path');

// __dirname is scripts/ directory
// From scripts/ we need to go: ../.. (to packages/javascript/drtrace-client) -> ../.. (to packages/javascript) -> ../.. (to root) -> agents
const sourceDir = path.resolve(__dirname, '../../../../agents');
const targetDir = path.resolve(__dirname, '../agents');

// Create target directory
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

// Copy all files recursively
function copyRecursive(src, dest, rootSrc) {
  // rootSrc tracks the original source directory to determine root-level files
  if (!rootSrc) {
    rootSrc = path.resolve(src);
  }
  
  const entries = fs.readdirSync(src, { withFileTypes: true });
  
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    
    if (entry.isDirectory()) {
      // Recursively copy directories
      if (!fs.existsSync(destPath)) {
        fs.mkdirSync(destPath, { recursive: true });
      }
      copyRecursive(srcPath, destPath, rootSrc);
    } else {
      // Copy files (no renaming needed - files are already named correctly)
      const finalDestPath = path.join(dest, entry.name);
      fs.copyFileSync(srcPath, finalDestPath);
      console.log(`Copied ${entry.name}`);
    }
  }
}

try {
  if (!fs.existsSync(sourceDir)) {
    console.warn(`Warning: Agents directory not found at ${sourceDir}`);
    process.exit(0);
  }
  
  copyRecursive(sourceDir, targetDir);
  console.log('✓ Successfully copied agent files');
} catch (error) {
  console.error(`Warning: Failed to copy agent files: ${error.message}`);
  process.exit(0); // Don't fail build
}

