# Changelog

## [1.2.0] - 2025-10-07

### Added
- **Vertical crosshair line** when clicking user messages
  - Yellow dashed line appears on both charts
  - Persists when toggling between time/message views
  - Automatically adjusts position based on current mode
- **Enhanced chart titles** showing clicked message details
  - Displays: User Message #X Cost: N tokens (duration date)
  - Updates dynamically when clicking different messages
- **Improved toggle function** to preserve crosshair position
  - Saves line data before mode change
  - Redraws in correct position after toggle

### Changed
- Chart title now updates with selected message context
- Toggle function preserves UI state better

### Feature Parity
- ✅ Now has complete feature parity with Codex version
- All interactive features from Codex version implemented

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
