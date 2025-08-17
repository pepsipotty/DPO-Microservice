#!/bin/bash

# DPO Reorg Commit Script
# Stages and commits reorganization changes in logical groups
# Pauses between commits for review - does NOT push

set -e

echo "🔄 DPO Reorganization Commit Script"
echo "====================================="
echo ""
echo "This script will create 5 commits for the completed reorganization:"
echo "1. feat: reorganize codebase into domain-driven architecture"
echo "2. feat: add configuration schemas and contracts" 
echo "3. chore: improve development experience and operations"
echo "4. docs: update documentation and planning artifacts"
echo "5. refactor: update imports and references"
echo ""
echo "Each commit will show a preview and pause for confirmation."
echo ""

# Commit 1: Core package reorganization
echo "📦 COMMIT 1: Core Architecture Reorganization"
echo "============================================="

git add core/
git add datasets/
git add storage/ 
git add training/
git add tools/
git rm preference_datasets.py

echo ""
echo "📋 Staged changes:"
git status --porcelain

echo ""
echo "📄 Diff preview (first 50 lines):"
git diff --staged --stat
echo ""

read -p "🤔 Proceed with commit 1? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "$(cat <<'EOF'
feat: reorganize codebase into domain-driven architecture

- Split monolithic structure into packages: core/, datasets/, storage/, training/, tools/
- Move preference_datasets.py to datasets/ package  
- Establish clear package boundaries for better maintainability
- Maintain 100% backward compatibility with existing APIs

EOF
)"
    echo "✅ Commit 1 completed"
else
    echo "❌ Commit 1 skipped"
    git reset
    exit 1
fi

echo ""

# Commit 2: Configuration schemas and contracts  
echo "📋 COMMIT 2: Configuration Schemas and Contracts"
echo "================================================"

git add config/schemas/
git add core/validators.py
git add datasets/__init__.py
git add storage/__init__.py

echo ""
echo "📋 Staged changes:"
git status --porcelain

echo ""
echo "📄 Diff preview:"
git diff --staged --stat
echo ""

read -p "🤔 Proceed with commit 2? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "$(cat <<'EOF'
feat: add configuration schemas and contracts

- Add JSON Schema validation for training, model, and loss configs
- Implement interface contracts for datasets and storage
- Add core validators for configuration validation  
- Enable safer configuration management with type checking

EOF
)"
    echo "✅ Commit 2 completed"
else
    echo "❌ Commit 2 skipped"
    git reset
    exit 1
fi

echo ""

# Commit 3: Development experience and operations
echo "🛠️  COMMIT 3: Development Experience and Operations"
echo "=================================================="

git add Makefile
git add .env.example
git add tests/test_api.py
git add Dockerfile

echo ""
echo "📋 Staged changes:"
git status --porcelain

echo ""
echo "📄 Diff preview:"
git diff --staged --stat
echo ""

read -p "🤔 Proceed with commit 3? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "$(cat <<'EOF'
chore: improve development experience and operations

- Add comprehensive Makefile with 20+ development commands
- Optimize Docker build with multi-layer caching
- Add .env.example for environment variable documentation
- Implement API integration tests for webhook endpoints

EOF
)"
    echo "✅ Commit 3 completed"
else
    echo "❌ Commit 3 skipped"
    git reset
    exit 1
fi

echo ""

# Commit 4: Documentation and planning
echo "📚 COMMIT 4: Documentation and Planning Artifacts"
echo "================================================="

git add plan/
git add README.md

echo ""
echo "📋 Staged changes:"
git status --porcelain

echo ""
echo "📄 Diff preview:"
git diff --staged --stat
echo ""

read -p "🤔 Proceed with commit 4? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "$(cat <<'EOF'
docs: update documentation and planning artifacts

- Add comprehensive reorganization planning documents
- Update README with new package structure and usage
- Document architectural decisions and validation results
- Include Mermaid diagrams for system architecture

EOF
)"
    echo "✅ Commit 4 completed"
else
    echo "❌ Commit 4 skipped" 
    git reset
    exit 1
fi

echo ""

# Commit 5: Import updates and references
echo "🔄 COMMIT 5: Import Updates and References"
echo "=========================================="

git add webhook_handler.py
# Note: __pycache__ files excluded as they'll be regenerated

echo ""
echo "📋 Staged changes:"
git status --porcelain

echo ""
echo "📄 Diff preview:"
git diff --staged --stat
echo ""

read -p "🤔 Proceed with commit 5? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "$(cat <<'EOF'
refactor: update imports and references

- Update import paths after package reorganization
- Maintain identical behavior with new package structure
- Ensure all modules reference correct package locations

EOF
)"
    echo "✅ Commit 5 completed"
else
    echo "❌ Commit 5 skipped"
    git reset  
    exit 1
fi

echo ""
echo "🎉 ALL COMMITS COMPLETED!"
echo "========================"
echo ""
echo "📊 Recent commit history:"
git log -5 --oneline --decorate
echo ""
echo "🔍 Last commit details:"
git show --stat HEAD
echo ""
echo "⚠️  NEXT STEPS:"
echo "1. Review commits: git log -5 --oneline"
echo "2. Test functionality: make test && make toy-trigger"
echo "3. Push when ready: git push origin HEAD"
echo ""
# Commented out - manual push required
# echo "🏷️  Optional: Create release tag"
# echo "git tag -a v1.0.0 -m 'DPO Microservice Reorganization - v1.0.0'"
echo ""
echo "✅ Commit script completed successfully!"