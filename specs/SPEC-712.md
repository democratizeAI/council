# SPEC-712 — Extract Lumina/MBQSP PDFs into `north_star.yaml`

**Specification ID:** SPEC-712  
**Owner:** Builder-tiny  
**Priority:** Medium  
**Status:** Queued (Freeze-Safe)

## Overview

Automated extraction script to parse Lumina equations, MBQSP principles, and unified field mathematics from PDF documentation into the centralized `north_star.yaml` configuration file.

## Scope

### In Scope
- Parse all PDFs in `/docs/pdfs/` directory
- Extract content matching patterns: "Equation", "Principle", "Tensor", "Purpose"
- Update `north_star.yaml` while preserving manual edits
- Validate YAML syntax and structure
- Log extraction results with success metrics

### Out of Scope
- OCR of scanned PDFs (text-based PDFs only)
- Complex mathematical symbol parsing beyond Unicode
- Version control of PDF sources
- Real-time monitoring (batch processing only)

## Implementation Requirements

### Core Functionality
```python
# Pseudocode structure
def extract_north_star():
    pdfs = scan_directory("docs/pdfs/")
    equations = extract_equations(pdfs)
    principles = extract_principles(pdfs) 
    tensors = extract_tensors(pdfs)
    purpose = extract_purpose(pdfs)
    
    update_yaml("north_star.yaml", {
        "lumina_equations": equations,
        "mbqsp_principles": principles, 
        "unified_axes": tensors,
        "purpose": purpose
    })
```

### Extraction Patterns
- **Equations**: Regex `r"Equation\s*\d*:\s*(.+?)"`
- **Principles**: Headers containing "Principle" or "MBQSP"
- **Tensors**: Mathematical expressions with tensor notation
- **Purpose**: Sections titled "Purpose", "Mission", "North Star"

### YAML Preservation
- Preserve existing comments and structure
- Only update extracted sections
- Maintain `kpi_targets` and `metadata` manually managed sections
- Backup original before modification

## Definition of Done (DoD)

- [ ] Script parses every PDF in `/docs/pdfs/` without errors
- [ ] Successfully extracts equations, principles, tensors, and purpose statements  
- [ ] Updates `north_star.yaml` preserving manual edits and comments
- [ ] CI job `yaml_lint` passes validation
- [ ] Script logs `yaml_updated=true` on successful completion
- [ ] Zero regression in existing YAML structure

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Extraction Success Rate | 100% | PDFs processed without errors |
| YAML Validity | Pass | `yamllint north_star.yaml` returns 0 |
| Update Confirmation | True | Log contains `yaml_updated=true` |
| Manual Edit Preservation | 100% | Comments and KPIs unchanged |

## Testing Criteria

### Unit Tests
- PDF parsing with malformed inputs
- YAML update with conflicting manual edits
- Regex pattern matching accuracy
- File backup and recovery

### Integration Tests  
- Full pipeline: PDFs → extraction → YAML update
- CI integration with lint validation
- Error handling and logging

## Rollback Plan

- Automatic backup before modification
- Git revert capability for failed extractions
- Manual override flag: `--skip-extraction`
- Validation gate prevents invalid YAML commits

## Dependencies

- **Python Libraries**: `PyPDF2`, `pyyaml`, `re`
- **CI Integration**: `.github/workflows/yaml-lint.yml`
- **File Access**: Read access to `/docs/pdfs/`, write to `north_star.yaml`

## Timeline

- **Effort Estimate**: 0.5 days
- **Blocked Until**: Freeze period completion
- **Auto-Trigger**: Builder-tiny scaffolding post-soak

## Notes

This spec remains dormant until the current freeze period lifts. Upon unfreezing, Builder-tiny will auto-scaffold the implementation as PR `builder/NS-110-extractor`. 