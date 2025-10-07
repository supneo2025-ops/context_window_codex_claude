# Codex vs Claude Code Context Visualizers

## Quick Comparison

| Aspect | Codex Context | Claude Context |
|--------|---------------|----------------|
| **Session Storage** | `~/.codex/sessions/YYYY/MM/DD/` | `~/.claude/projects/<project-name>/` |
| **File Format** | Event messages with `event_msg` type | Direct user/assistant message logs |
| **Token Tracking** | Dedicated `token_count` events | Embedded in assistant message usage |
| **User Messages** | `user_message` events | `user` type messages |
| **Cache Tokens** | ❌ Not tracked | ✅ Tracks cache creation & reads |
| **Model Context Window** | Configurable per model | Fixed at 200K (Claude default) |

## Session Format Examples

### Codex Session Format
```json
{
  "type": "event_msg",
  "payload": {
    "type": "token_count",
    "info": {
      "total_token_usage": {"total_tokens": 15000},
      "last_token_usage": {"total_tokens": 8000},
      "model_context_window": 272000
    }
  },
  "timestamp": "2025-10-07T03:41:58.340Z"
}
```

### Claude Code Session Format
```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [...],
    "usage": {
      "input_tokens": 5432,
      "output_tokens": 123,
      "cache_creation_input_tokens": 10957,
      "cache_read_input_tokens": 0
    }
  },
  "timestamp": "2025-10-07T03:41:58.340Z"
}
```

## Usage Comparison

### Codex Context
```bash
# Analyze latest sessions
python context_window_chart_v5.py --latest 1

# Analyze specific day
python context_window_chart_v5.py --day 2025-10-06

# Analyze since date
python context_window_chart_v5.py --since '2025-10-06'

# List recent
python context_window_chart_v5.py --hours 24
```

### Claude Context
```bash
# Analyze latest session
python context_window_chart_claude.py --latest

# Analyze by UUID
python context_window_chart_claude.py af2f56a6-9583-436e

# List recent
python context_window_chart_claude.py --list 24

# Custom output
python context_window_chart_claude.py --latest --output-dir ~/charts
```

## Token Calculation Differences

### Codex
- **Context Window**: `last_token_usage.total_tokens`
- **Cumulative**: `total_token_usage.total_tokens`
- Tracks total tokens only (no breakdown)

### Claude Code
- **Context Window**: `input_tokens + cache_creation_input_tokens`
- **Cumulative**: Sum of all `(input + cache_creation + output)` tokens
- Separate tracking of:
  - Input tokens
  - Output tokens
  - Cache creation tokens
  - Cache read tokens

## Chart Features

Both tools provide:
- ✅ Interactive time-series charts
- ✅ User message annotations
- ✅ Toggle between time-based and message-based x-axis
- ✅ Click-to-scroll message interaction
- ✅ Cost calculation per message
- ✅ Duration tracking
- ✅ Beautiful gradient UI

## File Organization

### Codex
```
~/.codex/sessions/
├── 2025/
│   └── 10/
│       └── 07/
│           ├── session1.jsonl
│           └── session2.jsonl
```

### Claude Code
```
~/.claude/projects/
├── -Users-username-project1/
│   ├── session1.jsonl
│   └── session2.jsonl
├── -Users-username-project2/
│   └── session3.jsonl
```

## When to Use Each

### Use Codex Context for:
- Analyzing Codex/OpenAI Codex sessions
- Time-series analysis across days
- DuckDB-powered date range queries
- Multi-session aggregation

### Use Claude Context for:
- Analyzing Claude Code sessions
- Project-based session analysis
- Cache token tracking
- Latest session quick analysis

## Migration Notes

If you're switching from Codex to Claude Code:
1. Session files are in a different location
2. Event format is different (no `event_msg` wrapper)
3. Token tracking is more detailed (cache tokens)
4. Projects are organized by directory, not by date
5. No day-based or date-range queries (yet)

## Future Enhancements

Potential improvements for Claude Context:
- [ ] Add DuckDB support for date range queries
- [ ] Multi-session aggregation
- [ ] Cache efficiency metrics
- [ ] Project-level analytics
- [ ] Export to CSV/JSON
- [ ] Compare multiple sessions side-by-side
