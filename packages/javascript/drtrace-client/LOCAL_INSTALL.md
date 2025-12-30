# Installing DrTrace from Local Folder

This guide explains how to install and test the `drtrace` npm package from a local folder instead of publishing to npm.

## Method 1: Using `npm install` with Local Path

### Step 1: Build the Package

First, make sure the package is built:

```bash
cd /media/thanh/data/Projects/wwi/packages/javascript/drtrace-client
npm run build
```

This will:
- Compile TypeScript to JavaScript
- Copy the `bin/init.js` file to `dist/bin/init.js`
- Make the binary executable

### Step 2: Install from Local Path

In your test project (folder A), install the package using the local path:

```bash
cd /path/to/folder/A
npm install /media/thanh/data/Projects/wwi/packages/javascript/drtrace-client
```

Or use a relative path:

```bash
cd /path/to/folder/A
npm install ../wwi/packages/javascript/drtrace-client
```

### Step 3: Verify Installation

```bash
# Check if package is installed
npm list drtrace

# Test the CLI command
npx drtrace init --help
```

## Method 2: Using `npm link` (Development)

This creates a symlink, useful for active development:

### Step 1: Link the Package

```bash
cd /media/thanh/data/Projects/wwi/packages/javascript/drtrace-client
npm link
```

### Step 2: Use in Test Project

```bash
cd /path/to/folder/A
npm link drtrace
```

### Step 3: Test

```bash
npx drtrace init --help
```

### Step 4: Unlink When Done

```bash
# In test project
npm unlink drtrace

# In package directory (optional)
npm unlink
```

## Method 3: Using `file:` Protocol in package.json

Add to your test project's `package.json`:

```json
{
  "dependencies": {
    "drtrace": "file:../wwi/packages/javascript/drtrace-client"
  }
}
```

Then run:

```bash
npm install
```

## Testing the CLI

After installation, test the init command:

```bash
# Show help
npx drtrace init --help

# Run initialization (interactive)
npx drtrace init

# Run with custom project root
npx drtrace init --project-root /path/to/project
```

## Troubleshooting

### Issue: "drtrace: not found"

**Solution**: Make sure the package is built:
```bash
cd /media/thanh/data/Projects/wwi/packages/javascript/drtrace-client
npm run build
```

### Issue: Binary not executable

**Solution**: The build script should handle this, but you can manually fix:
```bash
chmod +x dist/bin/init.js
```

### Issue: Module not found errors

**Solution**: Rebuild the package:
```bash
npm run build
```

## Running Tests

To verify everything works, run the test suite:

```bash
cd /media/thanh/data/Projects/wwi/packages/javascript/drtrace-client
npm test
```

Or run just the init tests:

```bash
npm test -- init.test.ts
```

## Notes

- The `prepare` script runs automatically on `npm install`, so the package will be built when installed
- Changes to source code require rebuilding: `npm run build`
- When using `npm link`, changes are reflected immediately (no rebuild needed for most changes)
- The binary file (`dist/bin/init.js`) must exist and be executable for `npx drtrace` to work

