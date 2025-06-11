# Manual System Implementation - 2025-01-07

## Context
Implementing the guidebook manual system for AI bots (o3, Opus) to provide them with operational knowledge.

## Key Decisions Made

### Manual Structure
- Created 6 essential manuals in `/guidebook/`:
  - `architecture.md` - System overview and data flow
  - `coding_standards.md` - Formatting and conventions
  - `patch_workflow.md` - Git PR flow and patchctl usage
  - `authz_roles.md` - Bot permissions and access control
  - `alert_runbook.md` - Alert triage and automated responses
  - `metrics_cheatsheet.md` - PromQL queries and monitoring
  - `deployment_checklist.md` - Deployment procedures and soak testing

### Technical Implementation
- **Guide Loader**: Python service that loads markdown files into Redis
- **Redis Storage**: `guide:docs` hash stores manual content with metadata
- **PatchCtl Integration**: Added `/manuals` endpoints for manual retrieval
- **Authorization**: Updated `authz.yaml` with detailed bot permissions

### Bot Permissions
- **robot-o3**: Source code, tests, Docker files
- **robot-opus**: Infrastructure, config, deployment scripts
- **robot-emergency**: Full access with manual approval required

## Lessons Learned

### What Worked Well
1. **Modular Design**: Separate manuals for different concerns
2. **Redis Integration**: Fast manual retrieval for bot context
3. **Comprehensive Coverage**: Manuals cover full operational lifecycle
4. **Clear Permissions**: Explicit role-based access control

### Challenges Encountered
1. **Manual Maintenance**: Need process to keep manuals current
2. **Context Size**: Large manuals may exceed bot context windows
3. **Version Control**: Manual changes need proper review process

### Future Improvements
1. **Auto-Update**: Trigger guide loader on manual file changes
2. **Chunking**: Split large manuals into smaller, focused sections
3. **Usage Analytics**: Track which manuals bots access most
4. **Validation**: Automated checks for manual consistency

## Implementation Notes

### Redis Schema
```
guide:docs -> Hash
  - architecture.md -> JSON{content, hash, metadata}
  - coding_standards.md -> JSON{content, hash, metadata}
  - ...

guide:metadata -> Hash
  - last_load -> JSON{loaded_files, timestamp, version}
```

### API Endpoints
- `GET /health` - Service status + available manuals
- `GET /manuals` - List all available manuals
- `GET /manuals/{name}` - Retrieve specific manual content

### Docker Services
- `guide_loader` - Loads manuals on startup
- `patchctl` - Enhanced with manual retrieval endpoints

## Next Steps

1. **Test Integration**: Verify bots can access manuals via API
2. **Conversation Embeddings**: Implement FAISS-based conversation search
3. **Monitoring**: Add metrics for manual usage and effectiveness
4. **Documentation**: Update main README with manual system overview

## Commands Used

```bash
# Create directory structure
mkdir guidebook conversations guide_loader

# Build and test guide loader
docker-compose build guide_loader
docker-compose up guide_loader

# Test manual retrieval
curl http://localhost:9000/manuals
curl http://localhost:9000/manuals/architecture.md

# Verify Redis storage
docker-compose exec redis redis-cli HGET guide:docs architecture.md
```

## Success Metrics

- [ ] All 6 manuals loaded into Redis successfully
- [ ] PatchCtl API returns manual content correctly
- [ ] Bot permissions enforced per authz.yaml
- [ ] Guide loader completes without errors
- [ ] Manual content accessible via /manuals endpoints

## Related Tickets

- #212 Guide-book Loader (Completed)
- #214 Conversation Warm-Start (Next)
- Future: Manual versioning and change detection 