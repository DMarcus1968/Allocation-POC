# Allocation-POC

Proof of concept for an allocation system.

## Project Overview

This repository is a POC (Proof of Concept) exploring allocation logic and workflows. As a POC, favor simplicity and clarity over production-grade abstractions.

## Development Guidelines

- Keep code simple and readable — this is a POC, not a production system
- Prefer flat project structure; avoid deep nesting until complexity demands it
- Write small, focused functions with clear names
- Include inline comments only where intent isn't obvious from the code itself
- Avoid premature abstraction — duplicate code is acceptable if it aids clarity

## Code Style

- Use consistent formatting throughout the project
- Prefer descriptive variable and function names over abbreviations
- Keep files focused on a single responsibility
- Handle errors at system boundaries (user input, external APIs), not internally

## Testing

- Write tests for core allocation logic
- Test edge cases: zero values, negative numbers, rounding, over/under-allocation
- Keep tests close to the code they verify

## Git Conventions

- Write concise commit messages that explain *why*, not just *what*
- One logical change per commit
- Branch names should be descriptive of the feature or fix
