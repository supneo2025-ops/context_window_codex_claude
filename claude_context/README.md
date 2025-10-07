# Claude Code Context Window Visualizer

Generate beautiful HTML visualizations of token usage for your Claude Code sessions.

## Features

- **Interactive Charts**: Visualize context window and cumulative token usage over time
- **User Message Tracking**: See exactly when you sent each message and how it affected token usage
- **Dual X-Axis Modes**: Toggle between time-based and message-based x-axis
- **Cost Analysis**: Calculate token cost per user message
- **Session Statistics**: View detailed stats about your coding session

## Installation

No special dependencies required beyond Python 3.10+. The tool uses only standard library modules.

```bash
# Make the script executable
chmod +x context_window_chart_claude.py
```

## Usage

### Analyze the Latest Session

```bash
python3 context_window_chart_claude.py --latest
```

### Analyze a Specific Session by UUID

```bash
python3 context_window_chart_claude.py af2f56a6-9583-436e-a6fa-2ded2db86900
```

### Analyze a Specific Session by Path

```bash
python3 context_window_chart_claude.py ~/.claude/projects/-Users-hungnx-PycharmProjects-tmp-context-window/af2f56a6-9583-436e-a6fa-2ded2db86900.jsonl
```

### List Recent Sessions

List sessions modified within the last 24 hours:
```bash
python3 context_window_chart_claude.py --list 24
```

List sessions from the last 2 hours:
```bash
python3 context_window_chart_claude.py --list 2
```

### Custom Output Directory

```bash
python3 context_window_chart_claude.py --latest --output-dir ~/Documents/claude_charts
```

### Time-Based X-Axis

By default, the chart uses message-based spacing. To use time-based:
```bash
python3 context_window_chart_claude.py --latest --time-based-x
```

### Filter Short Messages

Skip short user messages (like "yes", "ok", "continue") to focus on substantial interactions:
```bash
# Skip messages shorter than 10 characters
python3 context_window_chart_claude.py --latest --min-length 10

# Skip messages shorter than 20 characters
python3 context_window_chart_claude.py 52212cf5-8136-4530-845c --min-length 20
```

This is useful for sessions with many brief responses that clutter the visualization.

## Options

```
positional arguments:
  session_file          Path to session JSONL file or UUID to search for

optional arguments:
  --latest              Use the most recent session
  --list H              List sessions modified within last H hours (default: 24)
  --min-length N        Skip user messages shorter than N characters (default: 0, no filtering)
  --time-based-x        Use time-based x-axis instead of message-based
  --output-dir DIR      Output directory for HTML files (default: ./claude_context)
```

## How It Works

Claude Code stores session data in `~/.claude/projects/`. Each project directory contains `.jsonl` files with session data including:
- User messages
- Assistant responses
- Token usage statistics (input, output, cache tokens)
- Timestamps for all events

The visualizer:
1. Parses the JSONL session file
2. Extracts token usage and user messages
3. Calculates cumulative statistics and costs
4. Generates an interactive HTML chart using Chart.js
5. Auto-opens the chart in your default browser

## Output

The tool generates an HTML file with:
- **Context Window Chart**: Shows input tokens per API call
- **Cumulative Token Chart**: Shows total tokens used over time
- **User Messages Panel**: Lists all your messages with costs and timestamps
- **Statistics Panel**: Key metrics about the session

Click on user messages in the sidebar to highlight them on the charts!

## Example Output

```
Using latest session: /Users/hungnx/.claude/projects/-Users-hungnx-PycharmProjects-tmp-context-window/af2f56a6-9583-436e-a6fa-2ded2db86900.jsonl

Analyzing session: af2f56a6-9583-436e-a6fa-2ded2db86900.jsonl
  Found 23 token events
  Found 20 user messages
  Total messages: 45

Chart generated: claude_context/context_window_chart_af2f56a6-9583-436e-a6fa-2ded2db86900.html
  Final context: 443 tokens
  Cumulative total: 149,485 tokens
  Context usage: 0.2%
```

## Differences from Codex Context

This tool is adapted from the `codex_context` tool but designed specifically for Claude Code:

| Feature | Codex | Claude Code |
|---------|-------|-------------|
| Session location | `~/.codex/sessions/` | `~/.claude/projects/` |
| Session format | Event-based with `event_msg` type | Direct message logs with `user`/`assistant` types |
| Token tracking | `token_count` events | Token usage in assistant messages |
| Cache tokens | Not tracked | Tracks cache creation and cache read tokens |
| Project organization | By date | By project directory |

## Tips

- Use `--latest` for quick analysis of your current session
- Use `--list 1` to see all sessions from the last hour
- The HTML files are self-contained and can be shared or archived
- Toggle between message-based and time-based views to see different perspectives

## License

MIT
