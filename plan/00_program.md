# DPO Reorg Program

## Scope

**Objective**: Reorganize DPO microservice repository from monolithic structure to clean domain-driven architecture with proper separation of concerns.

**Target State**: 
- Separate `api/`, `training/`, `datasets/`, `storage/`, and `core/` domains
- Centralized configuration management under `config/` with environment separation
- Secure credential handling
- Clear module interfaces and reduced coupling
- Improved testability and maintainability

**Out of Scope**:
- Algorithm changes to DPO/SFT training logic
- Model architecture modifications
- Firebase storage backend replacement
- Performance optimizations

## Phases

### 1. Repo Cartographer ✓ COMPLETED
**Status**: Done
**Artifacts**: plan/01_cartography.md, plan/01_moves.json
**Outcome**: Identified 22 file moves, analyzed dependencies, documented current architecture issues

### 2. Config & Contracts Orchestrator (NEXT)
**Goal**: Establish configuration management and interface contracts
**Scope**: 
- Create schemas for configuration validation
- Add .env.example for environment variables
- Set up dataset interface contracts
- Validate configuration loading after moves
**Risk Level**: Medium (config path changes affect training behavior)

### 3. Trainer Splitter
**Goal**: Package training logic and create clean interfaces
**Scope**:
- Move training files to training/ package
- Create run_training() facade for API integration
- Update import paths and dependencies
**Risk Level**: High (core training logic movement)

### 4. Ops & DX Finisher
**Goal**: Complete operational setup and developer experience
**Scope**:
- Update Dockerfile for new structure
- Create Makefile for common operations
- Add API integration tests
- Update documentation
**Risk Level**: Low (operational improvements)

## Risks & Mitigations

### High Priority Risks
1. **Training Behavior Changes** (Impact: Critical)
   - Risk: Config path changes break Hydra resolution
   - Mitigation: Validate all config loading before deployment
   - Gate: Explicit user approval for training config moves

2. **Credential Exposure** (Impact: High)
   - Risk: serviceKey.json move might expose credentials
   - Mitigation: Move to environment variables, update .gitignore
   - Gate: Verify secure credential handling

3. **API Breaking Changes** (Impact: High)
   - Risk: Webhook handler path changes break external integrations
   - Mitigation: Maintain backward compatibility, test API endpoints
   - Gate: Validate API responses match current behavior

### Medium Priority Risks
4. **Import Path Breaks** (Impact: Medium)
   - Risk: Python import paths become invalid after moves
   - Mitigation: Update all import statements systematically
   - Validation: Import tests for all modules

5. **Docker Build Failures** (Impact: Medium)
   - Risk: Dockerfile context becomes invalid
   - Mitigation: Update COPY statements and test build
   - Validation: Full docker build test

## Decision Log

### 2025-08-17: Program Initialization
- **Decision**: Proceed with Minimal Crew approach (4 phases)
- **Rationale**: Balances thorough reorganization with manageable complexity
- **Approval**: Pending user confirmation for Config & Contracts phase

## Validation Strategy

### Phase Gates
- **Config & Contracts**: Hydra config resolution test, schema validation
- **Trainer Splitter**: Full training pipeline test (mock dataset)
- **Ops & DX**: Docker build test, API integration test

### Continuous Validation
```bash
# Configuration loading test
python -c "from hydra import initialize_config_dir, compose; print('Config OK')"

# Import validation test  
python -c "import training.train; import api.webhook_handler; print('Imports OK')"

# API endpoint test
curl -X POST localhost:8000/trigger_finetune -d '{"test": true}'

# Docker build test
docker build -t dpo-reorg-test .
```

## Timeline

- **Config & Contracts**: 1-2 hours (schemas, env setup, validation)
- **Trainer Splitter**: 2-3 hours (core moves, import updates, testing)  
- **Ops & DX**: 1-2 hours (docker, docs, final validation)
- **Total Estimated**: 4-7 hours

**Critical Path**: Config moves → Training moves → Docker updates
**Parallel Work**: Documentation can be updated alongside operational changes