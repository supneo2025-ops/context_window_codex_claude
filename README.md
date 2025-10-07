# Context Window Visualizers for Codex & Claude Code

Interactive HTML visualizations for token usage in AI coding sessions. Track context window usage, cumulative tokens, and analyze your coding conversations.

## 📊 What This Does

Generate beautiful, interactive charts showing:
- **Token usage over time** - See how your context window grows
- **User message tracking** - Click messages to highlight them on charts
- **Cost analysis** - Calculate token cost per interaction
- **Cache metrics** - Track prompt caching efficiency (Claude)
- **Session statistics** - Detailed metrics about your coding session

## 🚀 Quick Start

### For Claude Code Sessions
```bash
# Analyze your latest Claude Code session
python3 claude_context/context_window_chart_claude.py --latest

# Filter out short messages (like "yes", "ok")
python3 claude_context/context_window_chart_claude.py --latest --min-length 10

# Analyze a specific session by UUID
python3 claude_context/context_window_chart_claude.py af2f56a6-9583-436e
```

### For Codex Sessions
```bash
# Analyze latest session
python3 codex_context/context_window_chart_v5.py --latest 1

# Analyze specific day
python3 codex_context/context_window_chart_v5.py --day 2025-10-07

# Analyze date range
python3 codex_context/context_window_chart_v5.py --since '2025-10-06'
```

## 📁 Project Structure

```
.
├── claude_context/           # Claude Code session visualizer
│   ├── context_window_chart_claude.py
│   ├── README.md
│   ├── COMPARISON.md
│   └── CHANGELOG.md
│
├── codex_context/            # Codex session visualizer
│   ├── context_window_chart_v5.py
│   └── context_window_chart_v5.md
│
└── README.md                 # This file
```

## 🎯 Features

### Claude Code Visualizer (`claude_context/`)
- ✅ Parses sessions from `~/.claude/projects/`
- ✅ **Cache token tracking** (creation & read)
- ✅ Filter short messages with `--min-length`
- ✅ Project-based organization
- ✅ Lightweight - no dependencies except Python 3.10+

### Codex Visualizer (`codex_context/`)
- ✅ Parses sessions from `~/.codex/sessions/`
- ✅ Date-based organization
- ✅ DuckDB support for date range queries
- ✅ Multi-session aggregation
- ✅ Day-by-day analysis

## 📖 Documentation

Each visualizer has its own detailed documentation:
- [Claude Code Documentation](claude_context/README.md)
- [Codex Documentation](codex_context/context_window_chart_v5.md)
- [Comparison Guide](claude_context/COMPARISON.md)

## 🎨 Example Output

Both tools generate interactive HTML charts with:
- **Two time-series charts**: Context window and cumulative tokens
- **User message sidebar**: Click to highlight messages on charts
- **Toggle views**: Switch between time-based and message-based x-axis
- **Statistics panel**: Key metrics at a glance
- **Beautiful gradient UI**: Dark theme with smooth animations

## 🔧 Requirements

- Python 3.10+
- No external dependencies for basic usage
- Optional: DuckDB for Codex date range queries (`pip install duckdb`)

## 💡 Use Cases

### Track Context Window Growth
Understand how your context window fills up during long coding sessions.

### Optimize Token Usage
Identify which messages consume the most tokens and adjust your workflow.

### Analyze Session Patterns
See when you interact most with the AI and how long between messages.

### Cost Analysis
Calculate token costs per message to understand API usage.

### Filter Noise
Skip short messages (like "yes", "continue") to focus on substantial interactions.

## 📊 Real-World Example

A quantum-trading-system session:
- **292 user messages** → filtered to **9 meaningful messages** with `--min-length 10`
- **2.1M cumulative tokens** across 433 API calls
- **151K max context window** (largest single request)
- **HTML size**: 412KB → 143KB after filtering (65% reduction)

## 🤝 Contributing

Feel free to:
- Report issues
- Suggest features
- Submit pull requests
- Share your visualizations

## 📝 License

MIT License - See individual files for details

## 🙏 Credits

- Claude Code visualizer adapted from Codex context visualizer
- Built with [Chart.js](https://www.chartjs.org/)
- Made possible by Claude Code's session logging

## 🔗 Links

- [Claude Code](https://claude.com/claude-code)
- [Chart.js Documentation](https://www.chartjs.org/docs/)

---

**Made with ❤️ for AI-assisted coding**
