# Changelog

## [1.1.0] - 2025-10-07

### Added
- `--min-length N` flag to filter out short user messages
  - Skips messages shorter than N characters
  - Useful for removing brief responses like "yes", "ok", "continue"
  - Helps declutter visualizations for sessions with many short interactions
  - Example: `--min-length 10` to skip messages under 10 chars

### Example Impact
For quantum-trading-system session `52212cf5-8136-4530-845c`:
- Without filter: 292 user messages, 412KB HTML
- With `--min-length 10`: 9 user messages, 143KB HTML (65% reduction)
- With `--min-length 20`: 8 user messages

## [1.0.0] - 2025-10-07

### Initial Release
- Parse Claude Code session files from `~/.claude/projects/`
- Extract token usage and user messages
- Generate interactive HTML charts with Chart.js
- Context window and cumulative token tracking
- Cache token support (creation & read)
- Toggle between time-based and message-based x-axis
- Click-to-highlight message interactions
- Session statistics panel
- Auto-open generated charts
- Support for:
  - `--latest`: Analyze most recent session
  - `--list H`: List sessions from last H hours
  - `--time-based-x`: Time-based x-axis
  - `--output-dir`: Custom output directory
  - Session selection by path or UUID
