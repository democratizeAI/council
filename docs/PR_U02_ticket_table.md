# PR U-02: Live Ticket Table Component

**Label**: `autonomous`  
**Timeline**: T-24h  
**Status**: ✅ READY FOR MERGE

## 📋 Summary

Implements live ticket visualization as identified in UI Compliance Audit Matrix. This PR adds the missing ticket table component to enable the flow: **Every new row auto-appears → Click opens GitHub PR scaffold**.

## 🎯 Changes Made

### 1. New Component (`agent0-ui/src/components/TicketTable.tsx`)

**Key Features**:
- ✅ Auto-refresh every 30 seconds
- ✅ Live status indicators (open/in_progress/merged/failed)
- ✅ Click-to-open GitHub PR links
- ✅ Real-time ticket count and status distribution
- ✅ Error handling with retry functionality
- ✅ Loading states and responsive design

**Status Mapping**:
```typescript
🟢 → 'merged'   (green)
🔴 → 'failed'   (red)  
🟡 → 'in_progress' (yellow)
○  → 'open'     (blue)
```

### 2. App Integration (`agent0-ui/src/App.tsx`)

**Layout Updates**:
- Added ticket table toggle in header
- Integrated 3-panel layout: Chat | Tickets | Metrics
- Responsive design maintains usability
- Toggle controls for all panels

### 3. API Integration

**Expected Backend Endpoint**:
```
GET /ledger
{
  "rows": [
    {
      "id": "R-123",
      "ticket": "Create hello world function",
      "owner": "FE",
      "wave": "Ease-of-Use",
      "status": "🟡",
      "pr_url": "https://github.com/agent0/scaffold/pull/456",
      "created_at": "2025-06-10T19:00:00Z",
      "updated_at": "2025-06-10T19:15:00Z"
    }
  ]
}
```

## ✅ Audit Gap Resolution

| Requirement | Status Before | Status After |
|-------------|---------------|--------------|
| **Every new row auto-appears** | 🔴 **GAP** | ✅ **RESOLVED** |
| **Click opens GitHub PR scaffold** | 🔴 **GAP** | ✅ **RESOLVED** |
| **Real-time status updates** | - | ✅ **IMPLEMENTED** |
| **Error handling & retry** | - | ✅ **IMPLEMENTED** |

## 🎨 Visual Design

### Table Layout
```
┌─────────────────────────────────────┐
│ Live Tickets        🟢 Updated 19:24│
├─────────────────────────────────────┤
│ 🟡 in_progress  #R-123              │
│ Create hello world function         │
│ Owner: FE  Wave: Ease-of-Use  →     │
├─────────────────────────────────────┤
│ 🟢 merged      #R-122               │
│ Add user authentication             │
│ Owner: BE  Wave: Security  →        │
└─────────────────────────────────────┘
```

### Status Colors & Icons
- **🟢 Merged**: Green background, checkmark icon
- **🔴 Failed**: Red background, X icon  
- **🟡 In Progress**: Yellow background, ellipsis icon
- **○ Open**: Blue background, circle icon

## 🔄 Auto-Refresh Logic

### Polling Strategy
- **Interval**: 30 seconds (configurable)
- **Error Backoff**: Exponential backoff on failures
- **Connection Status**: Visual indicator in header
- **Background Updates**: Non-disruptive refresh

### Performance Optimization
- **Diff Updates**: Only re-render changed tickets
- **Max Height**: Scrollable with fixed 96px max height
- **Lazy Loading**: Efficient for large ticket lists

## 🧪 Testing Validation

### Manual Test Steps
1. Start Agent-0 with `/ledger` endpoint
2. Create test ticket via `/ledger/new`  
3. Verify ticket appears in table within 30s
4. Click ticket row → GitHub PR opens
5. Update ticket status → verify color change
6. Test error handling with service down

### Expected Behavior
- ✅ New tickets appear without refresh
- ✅ PR links open in new tab
- ✅ Status changes reflect immediately
- ✅ Graceful error handling with retry

## 🎯 Integration with Workflow

### BC-140 → BC-130 Flow
1. **BC-140**: `day1_injector.py` creates ticket
2. **Ledger**: Ticket appears in `/ledger` endpoint  
3. **UI**: Table auto-refreshes and shows new ticket
4. **Builder**: PR scaffold opens automatically
5. **UI**: Click opens GitHub PR for review

### Council Smoke-Cycle
- Tickets show autonomous PR creation
- Status updates reflect CI/merge progress
- Failed builds show red status immediately
- Successful merges show green with PR links

## 📊 Monitoring Integration

### New Metrics Available
- Ticket count by status (open/progress/merged/failed)
- Auto-refresh success rate
- PR click-through rate  
- Error rate for `/ledger` endpoint

### Dashboard Integration
- Real-time ticket count in header
- Status distribution in footer
- Connection health indicator
- Last update timestamp

## 🔄 Backward Compatibility

- ✅ Existing chat functionality unchanged
- ✅ Metrics sidebar remains independent
- ✅ Progressive enhancement (works without `/ledger`)
- ✅ Responsive design maintains mobile usability

## 🎯 Next Steps

After merge:
1. Integrate with BC-140 injector workflow
2. Add ticket filtering/sorting options
3. Implement ticket action buttons (retry/cancel)
4. Add ticket creation from chat interface

## 📊 Risk Assessment

**Risk**: LOW  
**Reason**: Self-contained component with graceful degradation

**Rollback Plan**:
- Hide ticket table via toggle  
- No impact on core chat functionality
- Component can be disabled via feature flag

---

**Ready for autonomous merge** - Resolves critical UI audit gaps with robust auto-refresh and GitHub integration. 