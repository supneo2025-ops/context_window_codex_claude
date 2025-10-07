# 📊 Context Window Chart v5 - User Guide

**Author:** Agent Claude (`3c66d982-896e-416c-a271-bb32d21ec313`)
**Location:** `/Users/sotola/swe/codex-analytics/context_window_chart_v5.py`

---

## 🎯 Overview

This tool analyzes Codex session JSONL files and generates interactive HTML dashboards with dual charts showing:

1. **Context Window Over Time** - Tracks the current conversation context size (from `last_token_usage`)
2. **Cumulative Total Tokens** - Shows all tokens processed throughout the session (from `total_token_usage`)

Both charts include scatter plot markers for user messages, allowing you to see exactly when interactions occurred and how they affected token usage.

---

## 🚀 Quick Start

### Analyze a Single Session

```bash
# By file path
python context_window_chart_v5.py \
  /Users/sotola/.codex/sessions/2025/10/03/rollout-2025-10-03T20-36-59-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl

# By UUID (auto-searches all sessions)
python context_window_chart_v5.py 0199aa4a-4aaa-7a71-ab74-320df9983ce1
```

### Analyze Latest N Sessions

```bash
# Generate charts for the 5 most recent sessions
python context_window_chart_v5.py --latest 5
```

### Analyze Sessions Since a Date

```bash
# All sessions with messages since Oct 6, 2025
python context_window_chart_v5.py --since '2025-10-06'

# With specific time
python context_window_chart_v5.py --since '2025-10-06 10:00:00'

# Underscore format also works
python context_window_chart_v5.py --since '2025_10_06'
```

### Analyze Sessions for a Specific Day

```bash
# All unique agent sessions from Oct 3, 2025
python context_window_chart_v5.py --day '2025-10-03'
```

### List Recent Sessions

```bash
# List sessions modified in the last 24 hours
python context_window_chart_v5.py --hours 24
```

---

## 📋 Command Line Arguments

| Flag | Description |
|------|-------------|
| `session_file` | Path to a specific Codex session JSONL file OR a UUID to search for |
| `--latest N` | Analyze the latest N sessions from `~/.codex/sessions` |
| `--since DATETIME` | Analyze sessions with messages since given datetime (uses DuckDB for efficient querying) |
| `--day YYYY-MM-DD` | Analyze all unique agent sessions for a specific day |
| `--hours H` | List sessions modified within the last H hours (does not generate charts) |
| `--time-based-x` | Use time-based x-axis instead of message-based (default is message-based) |
| `--output-dir` | Output directory for HTML files (default: `/Users/sotola/ai/generated_artifacts`) |
| `-h, --help` | Show help message with examples |

> **Note:** You must provide exactly one of: `session_file/UUID`, `--latest N`, `--since DATETIME`, `--day YYYY-MM-DD`, or `--hours H`

### Supported Date Formats for `--since`

- `2025-10-06` - Date only
- `2025_10_06` - Date with underscores
- `2025-10-06 10:00` - Date and time (hour:minute)
- `2025-10-06 10:00:00` - Date and time with seconds

---

## 🧠 Core Logic Explained

### Token Data Interpretation

The Codex API provides two critical metrics in each `token_count` event:

```python
# Extract from payload.info
total_usage = info.get('total_token_usage', {})  # Cumulative across entire session
last_usage = info.get('last_token_usage', {})    # Just the last request

# Cumulative total tokens (already summed by API)
cumulative_total = total_usage.get('total_tokens', 0)

# Context window (current conversation size)
context_tokens = last_usage.get('total_tokens', 0)
```

**Key Insight:**
- `total_token_usage.total_tokens` is **already cumulative** - we don't sum it ourselves
- `last_token_usage.total_tokens` represents the **actual context window** size for that turn

### Message Index Tracking

Each user message gets two indices:

```python
user_message_index = 0
with open(session_file) as f:
    for message_index, line in enumerate(f, 1):
        if payload.get('type') == 'user_message':
            user_message_index += 1
            user_messages.append({
                'user_msg_index': user_message_index,  # Nth user message
                'total_msg_index': message_index        # Mth message overall
            })
```

This allows tracking like: "User Message #11 was the 1,120th message overall in the session"

---

## 📊 Dashboard Features

### Header Section

- **Session ID** - Displayed prominently at the top
- **Date Range** - Shows session date(s) in format `2025_10_03` or `2025_10_03 → 2025_10_04` for multi-day sessions
- **X-Axis Toggle** - Switch between message-based and time-based x-axis (right side)

### Statistics Cards (Top Row)

- **Token Events** - Number of `token_count` events
- **User Messages** - Count of user interactions
- **Total Messages** - All JSONL lines in the session
- **Final Context** - Current context size (last turn)
- **Total** - All tokens processed (cumulative)
- **Model CW** - Model context window limit (272K)
- **Context Usage** - Percentage of context window used

### Chart 1: Context Window Over Time 🔵

Shows how the conversation context grows with each turn. Includes:
- Blue line for context tokens
- Red dashed line at 272K limit
- ⭐ Gold stars for user messages (clickable!)
- Dynamic title showing selected message cost and execution time

### Chart 2: Cumulative Total Tokens 🟣

Shows the running total of all tokens processed. Useful for understanding total API usage.
- Purple line for cumulative tokens
- ⭐ Gold stars for user messages (clickable!)
- Dynamic title showing selected message cost and execution time

### Chat Pane (Right Side)

Displays all user messages in reverse chronological order (newest first) with:
- **User Message #N** - Which user message number
- **Execution Time** - Duration from user message to next message (e.g., "4m 22s Oct 04")
- **Message #M** - Position in overall session
- **Message Text** - Truncated to 400 chars with middle omission
- **Context** - Context size when message was sent
- **Cumulative Total** - Total tokens in parentheses
- **Cost** - Tokens consumed between this message and the next (highlighted)
- **Timestamp** - HH:MM:SS format
- **Click to Highlight** - Clicking a card adds a golden border and draws vertical line on both charts

---

## 🎨 Interactive Features

### Click on Message Cards
When you click on a message card in the chat pane:
- The card gets a **golden border** with glow effect
- A **vertical golden line** appears on both charts at that message's position
- Chart titles update to show: **"• User Message #N Cost: X tokens (Xm Ys DATE)"**
- The card auto-scrolls into view (centered)

### Click on Star Markers
When you click on a ⭐ gold star marker in the charts:
- The corresponding message card in the chat pane gets highlighted with golden border
- The card auto-scrolls into view (centered in the pane)
- A vertical golden line appears on both charts
- Chart titles update to show cost and execution time

### Hover Over Stars
When you hover over a ⭐ gold star marker on the charts:

```
👤 User Message (#11)                    message #1120

Search for all code file from this folder and its
subfolders that's about using duck db to query codex
data (session data) at ~/.codex...

Cost: 2,547 tokens
```

The tooltip shows:
- User message number (#11)
- Total message number (#1120)
- Full message text (wrapped at 60 characters)
- Cost in tokens (consumed until next message)

### Toggle X-Axis Mode
Click the toggle switch in the header to switch between:
- ✓ **Message-based spacing** - X-axis shows message indices (1, 2, 3...) with interpolated timestamps
- ✕ **Time-based spacing** - X-axis shows actual timestamps with proper time scaling

The toggle preserves the vertical golden line indicator when switching modes.

### Responsive Layout

- Charts take 3/4 width, chat pane 1/4
- Both extend to bottom of viewport
- Scrollable chat pane with custom purple scrollbar
- Charts aligned perfectly with chat pane bottom edge
- Message cards have hover effects (slide left, border glow)

---

## 🔍 Example Output

### Using --latest
```bash
$ python context_window_chart_v5.py --latest 5

Found 1037 total sessions, using latest 5:
  1. rollout-2025-10-04T02-30-23-0199ab8d-d5a1-7df3-998e-8e3bc1ce56fc.jsonl
  2. rollout-2025-10-04T04-07-58-0199abe7-2e6c-74c3-aed8-ff2c1d4dc520.jsonl
  ...

Analyzing session: rollout-2025-10-04T02-30-23-0199ab8d-d5a1-7df3-998e-8e3bc1ce56fc.jsonl
  Found 513 token_count events
  Found 22 user messages
  Total messages in session: 1794
  Stats:
    First timestamp: 2025-10-04T02:30:23.573Z
    Last timestamp:  2025-10-04T06:15:42.891Z
    Final context:   267,796 tokens
    Cumulative total: 37,741,804 tokens
    Context usage: 98.5%

Summary:
  Total sessions analyzed: 5
  Total token events: 835
  Total user messages: 54
  Charts generated: 5

Opening 5 chart(s)...
```

### Using --since
```bash
$ python context_window_chart_v5.py --since '2025-10-06'

Finding sessions with messages since 2025-10-06 00:00:00...
Found 12 session(s) with messages since 2025-10-06 00:00:00:
  1. 0199aa4a-4aaa-7a71-ab74-320df9983ce1 | 347 messages | rollout-2025-10-06T08-15-32-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl (modified 2025-10-06 14:22:15)
  2. 0199ab12-5f67-8901-bc23-456def789012 | 124 messages | rollout-2025-10-06T10-30-45-0199ab12-5f67-8901-bc23-456def789012.jsonl (modified 2025-10-06 16:45:33)
  ...

Analyzing session: rollout-2025-10-06T08-15-32-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl
  Found 142 token_count events
  Found 18 user messages
  Total messages in session: 347
  ...
```

### Using --day
```bash
$ python context_window_chart_v5.py --day '2025-10-03'

Found 8 unique agent session(s) in /Users/sotola/.codex/sessions/2025/10/03:
  1. 0199aa4a-4aaa-7a71-ab74-320df9983ce1 -> rollout-2025-10-03T20-36-59-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl (modified 2025-10-03 23:45:12)
  2. 0199ab12-5f67-8901-bc23-456def789012 -> rollout-2025-10-03T14-22-30-0199ab12-5f67-8901-bc23-456def789012.jsonl (modified 2025-10-03 18:30:45)
  ...
```

### Using UUID Search
```bash
$ python context_window_chart_v5.py 0199aa4a-4aaa-7a71-ab74-320df9983ce1

Found 3 session(s) matching UUID '0199aa4a-4aaa-7a71-ab74-320df9983ce1':
  1. /Users/sotola/.codex/sessions/2025/10/06/rollout-2025-10-06T08-15-32-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl
  2. /Users/sotola/.codex/sessions/2025/10/05/rollout-2025-10-05T14-22-11-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl
  3. /Users/sotola/.codex/sessions/2025/10/03/rollout-2025-10-03T20-36-59-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl

Analyzing session: rollout-2025-10-03T20-36-59-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl
  ...
```

---

## 📁 Output Files

Charts are saved with descriptive names:

**Single session:**
```
context_window_chart_rollout-2025-10-03T20-36-59-0199aa4a-4aaa-7a71-ab74-320df9983ce1.html
```

**Multiple sessions via --latest:**
```
context_window_chart_rollout-2025-10-04T02-30-23-0199ab8d-d5a1-7df3-998e-8e3bc1ce56fc.html
context_window_chart_rollout-2025-10-03T20-36-59-0199aa4a-4aaa-7a71-ab74-320df9983ce1.html
context_window_chart_rollout-2025-10-01T15-36-14-01999eea-3a55-7701-a873-33dca80a9a70.html
```

---

## 🛠️ Technical Details

### Dependencies

```bash
# Required for --since flag only
pip install duckdb
```

**Core functionality** uses Python standard library only - no external dependencies!

**Optional dependency:**
- `duckdb>=1.0.0` - Required only for `--since` flag to efficiently query JSONL files by timestamp

### Data Structure

Session JSONL files contain events like:

```json
{
  "timestamp": "2025-10-03T17:24:39.573Z",
  "type": "event_msg",
  "payload": {
    "type": "token_count",
    "info": {
      "total_token_usage": {
        "total_tokens": 16063200  // Cumulative across session
      },
      "last_token_usage": {
        "total_tokens": 185928    // Current context window
      },
      "model_context_window": 272000
    }
  }
}
```

---

## 💡 Use Cases

### 1. Debug Context Window Issues
When you hit context limits, use this tool to see exactly when and how your context grew:

```bash
# By file path
python context_window_chart_v5.py ~/.codex/sessions/2025/10/03/problem-session.jsonl

# By UUID (finds all sessions with that UUID)
python context_window_chart_v5.py 0199aa4a-4aaa-7a71-ab74-320df9983ce1
```

### 2. Analyze Recent Activity
Check your last few sessions to understand token usage patterns:

```bash
python context_window_chart_v5.py --latest 10
```

### 3. Find Sessions from a Specific Date
Analyze all sessions that had activity on or after a certain date:

```bash
# All sessions with messages since Oct 6
python context_window_chart_v5.py --since '2025-10-06'

# Sessions since a specific time
python context_window_chart_v5.py --since '2025-10-06 14:30:00'
```

### 4. Daily Session Analysis
Review all unique agent sessions from a specific day:

```bash
python context_window_chart_v5.py --day '2025-10-03'
```

### 5. List Active Sessions
See what sessions have been active recently without generating charts:

```bash
python context_window_chart_v5.py --hours 24
```

### 6. Track Execution Time per Message
Click on any message card to see:
- How long Claude took to respond
- How many tokens were consumed
- The exact cost of that interaction

---

## 🎨 Visual Style

The dashboard features:
- 🌈 **Blue → Purple → Magenta gradient** background
- 📊 **Dual stacked charts** with responsive heights
- 💬 **Scrollable chat pane** with message cards
- ⭐ **Star markers** for user interactions
- 🎯 **Context window limit line** (red dashed)

---

## 🐛 Troubleshooting

### No Token Data Found
Some sessions may not have `token_count` events. The script automatically skips these:

```
Analyzing session: rollout-2025-10-04T04-07-58.jsonl
  Found 0 token_count events
  Skipping (no token data)
```

### DuckDB Not Installed
If you use `--since` without DuckDB installed:

```
Error: DuckDB is required for --since flag. Install with: pip install duckdb
```

**Solution:** Install DuckDB:
```bash
pip install duckdb
```

### Charts Not Opening
Ensure you have a browser associated with `.html` files. The script uses `open` command on macOS.

### Large Sessions
For sessions with 100K+ messages, loading may take a few seconds. The charts handle large datasets efficiently using Chart.js time-series rendering.

### Multiple Sessions with Same UUID
When searching by UUID, the script finds all matching sessions across all dates and generates a chart for each one. This is intentional - you can see the evolution of a long-running agent conversation over multiple days.

---

## 📞 Support

**Agent Contact:** Claude `3c66d982-896e-416c-a271-bb32d21ec313`

For questions, issues, or feature requests related to this tool, reference this agent ID in your session.

---

*Made by Claude Code - /Users/sotola/swe/codex-analytics*
