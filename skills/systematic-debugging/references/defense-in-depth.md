# Defense-in-depth validation

What to add after the root cause is found so the same bug cannot come back: a check at every layer the bad data passes through. The examples are TypeScript; the method applies to any language.

## Overview

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, or mocks.

**Core principle:** validate at every layer the data passes through. Make the bug structurally impossible.

## Why multiple layers

A single validation: "We fixed the bug."
Multiple layers: "We made the bug impossible."

Different layers catch different cases:

- Entry validation catches most bugs.
- Business logic catches edge cases.
- Environment guards prevent context-specific dangers.
- Debug logging helps when the other layers fail.

## The four layers

### Layer 1: Entry point validation

**Purpose:** reject obviously invalid input at the API boundary.

```typescript
function createProject(name: string, workingDirectory: string) {
  if (!workingDirectory || workingDirectory.trim() === '') {
    throw new Error('workingDirectory cannot be empty');
  }
  if (!existsSync(workingDirectory)) {
    throw new Error(`workingDirectory does not exist: ${workingDirectory}`);
  }
  if (!statSync(workingDirectory).isDirectory()) {
    throw new Error(`workingDirectory is not a directory: ${workingDirectory}`);
  }
  // ... proceed
}
```

### Layer 2: Business logic validation

**Purpose:** ensure the data makes sense for this operation.

```typescript
function initializeWorkspace(projectDir: string, sessionId: string) {
  if (!projectDir) {
    throw new Error('projectDir required for workspace initialization');
  }
  // ... proceed
}
```

### Layer 3: Environment guards

**Purpose:** prevent dangerous operations in specific contexts.

```typescript
async function gitInit(directory: string) {
  // In tests, refuse git init outside temp directories
  if (process.env.NODE_ENV === 'test') {
    const normalized = normalize(resolve(directory));
    const tmpDir = normalize(resolve(tmpdir()));

    if (!normalized.startsWith(tmpDir)) {
      throw new Error(
        `Refusing git init outside temp dir during tests: ${directory}`
      );
    }
  }
  // ... proceed
}
```

### Layer 4: Debug instrumentation

**Purpose:** capture context for forensics.

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  logger.debug('About to git init', {
    directory,
    cwd: process.cwd(),
    stack,
  });
  // ... proceed
}
```

## Applying the pattern

When you find a bug:

1. **Trace the data flow.** Where does the bad value originate? Where is it used?
2. **Map all checkpoints.** List every point the data passes through.
3. **Add validation at each layer.** Entry, business, environment, debug.
4. **Test each layer.** Try to bypass layer 1 and verify layer 2 catches it.

## Worked example

Bug: an empty `projectDir` caused `git init` in the source code folder.

**Data flow:**

1. Test setup produces an empty string.
2. `Project.create(name, '')`
3. `WorkspaceManager.createWorkspace('')`
4. `git init` runs in `process.cwd()`

**Four layers added:**

- Layer 1: `Project.create()` validates not empty, exists, is a directory.
- Layer 2: `WorkspaceManager` validates projectDir is not empty.
- Layer 3: `WorktreeManager` refuses git init outside tmpdir in tests.
- Layer 4: stack trace logging before git init.

**Result:** all 1847 tests passed, and the bug was impossible to reproduce.

## Key insight

All four layers were necessary. During testing, each layer caught bugs the others missed:

- Different code paths bypassed entry validation.
- Mocks bypassed business logic checks.
- Edge cases on different platforms needed environment guards.
- Debug logging identified structural misuse.

Don't stop at one validation point. Add checks at every layer.
