#!/usr/bin/env node

/**
 * Build script for generating BetterWebhooks.spl artifact
 * This script is designed to be used in GitHub CI/CD pipeline
 * Cross-platform compatible (Windows, macOS, Linux)
 */

const shell = require("shelljs");
const path = require("path");
const os = require("os");

// Ensure we exit on any error
shell.config.fatal = true;

const isWindows = process.platform === "win32";
const tempDir = isWindows ? process.env.TEMP : "/tmp";
const targetDir = path.join(tempDir, "BetterWebhooks");
const rootDir = process.cwd();

console.log("Starting BetterWebhooks build process...");
console.log(`Platform: ${process.platform}`);
console.log(`Root directory: ${rootDir}`);

try {
  // Step 1: Run yarn setup
  console.log("Step 1: Running yarn setup...");
  const setupResult = shell.exec("yarn run setup");
  if (setupResult.code !== 0) {
    throw new Error("yarn setup failed");
  }

  // Step 2: Change to better-webhooks directory
  console.log("Step 2: Changing to packages/better-webhooks directory...");
  const workflowsDir = path.join(rootDir, "packages", "better-webhooks");
  shell.cd(workflowsDir);
  console.log(`Current directory: ${shell.pwd()}`);

  // Step 3: Run yarn build
  console.log("Step 3: Running yarn build...");
  const buildResult = shell.exec("yarn run build");
  if (buildResult.code !== 0) {
    throw new Error("yarn build failed");
  }

  // Step 4: Move stage directory to temp/BetterWebhooks
  console.log(`Step 4: Moving stage directory to ${targetDir}...`);

  // Remove existing target directory if it exists
  if (shell.test("-d", targetDir)) {
    console.log(`Removing existing ${targetDir} directory...`);
    shell.rm("-rf", targetDir);
  }

  // Move stage directory
  const stageDir = path.join(workflowsDir, "stage");
  if (!shell.test("-d", stageDir)) {
    throw new Error("Stage directory not found. Build may have failed.");
  }

  shell.mv(stageDir, targetDir);
  console.log(`Successfully moved stage to ${targetDir}`);

  // Step 5: Create the .spl archive
  console.log("Step 5: Creating BetterWebhooks.spl archive...");

  // Change to temp directory to ensure correct archive structure
  shell.cd(tempDir);

  // Create the archive
  const archiveName = "BetterWebhooks.spl";
  const tarResult = shell.exec(`tar -czf ${archiveName} BetterWebhooks`);
  if (tarResult.code !== 0) {
    throw new Error("Failed to create tar archive");
  }

  // Move the .spl file back to the root directory
  console.log("Moving BetterWebhooks.spl to root directory...");
  const archivePath = path.join(tempDir, archiveName);
  const finalArchivePath = path.join(rootDir, archiveName);

  // Remove existing archive if it exists
  if (shell.test("-f", finalArchivePath)) {
    shell.rm(finalArchivePath);
  }

  shell.mv(archivePath, finalArchivePath);

  console.log("Build complete! BetterWebhooks.spl has been created successfully.");
  console.log(`Archive location: ${finalArchivePath}`);

  // Optional: Show the contents of the archive for verification
  console.log("Archive contents (first 20 files):");
  const listResult = shell.exec(`tar -tzf "${finalArchivePath}"`, {
    silent: true,
  });
  if (listResult.code === 0) {
    const files = listResult.stdout.split("\n").filter((line) => line.trim());
    files.slice(0, 20).forEach((file) => console.log(`  ${file}`));
    if (files.length > 20) {
      console.log(`  ... and ${files.length - 20} more files`);
    }
    console.log(`Total files in archive: ${files.length}`);
  }

  // Show archive size
  const stats = shell.ls("-l", finalArchivePath);
  console.log(`Archive size: ${stats[0].size} bytes`);

  process.exit(0);
} catch (error) {
  console.error("Build failed:", error.message);
  process.exit(1);
}
