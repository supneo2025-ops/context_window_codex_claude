#!/usr/bin/env python3
"""
Generate context window usage chart for a Codex session with user message annotations.
Shows cumulative token usage (input + output) over time with scatter points for user messages.
Includes a chat pane showing all user messages.

Made by Claude Code - /Users/sotola/swe/codex-analytics
"""

try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except Exception:
    pass

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False


SESSIONS_ROOT = Path.home() / '.codex' / 'sessions'
UUID_PATTERN = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', re.IGNORECASE)


def extract_uuid_from_name(name: str) -> str | None:
    """Pull a UUID out of a session filename."""
    match = UUID_PATTERN.search(name)
    return match.group(1) if match else None


def format_age(delta: timedelta) -> str:
    """Return a compact human-readable age string (e.g. '2h 3m')."""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"

    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"

    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"

    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def extract_session_data(session_file: Path) -> tuple:
    """Extract token_count events and user_message events from session JSONL."""
    token_data = []
    user_messages = []

    # Count total messages first
    with open(session_file) as f:
        total_message_count = sum(1 for _ in f)

    user_message_index = 0
    with open(session_file) as f:
        for message_index, line in enumerate(f, 1):
            try:
                record = json.loads(line)
                if record.get('type') == 'event_msg' and isinstance(record.get('payload'), dict):
                    payload = record['payload']
                    ts = record.get('timestamp', '')

                    # Extract token counts
                    if payload.get('type') == 'token_count' and payload.get('info'):
                        info = payload['info']
                        total_usage = info.get('total_token_usage', {})
                        last_usage = info.get('last_token_usage', {})

                        # Cumulative total tokens
                        cumulative_total = total_usage.get('total_tokens', 0)

                        # Context window (last request tokens)
                        context_tokens = last_usage.get('total_tokens', 0)

                        model_context_window = info.get('model_context_window', 272000)

                        # Parse timestamp to epoch milliseconds
                        ts_dt = datetime.fromisoformat(ts.rstrip('Z'))
                        ts_ms = int(ts_dt.timestamp() * 1000)

                        token_data.append({
                            'ts': ts,
                            'ts_ms': ts_ms,
                            'cumulative_total': cumulative_total,
                            'context_tokens': context_tokens,
                            'model_context_window': model_context_window,
                            'message_index': message_index
                        })

                    # Extract user messages
                    elif payload.get('type') == 'user_message':
                        user_message_index += 1
                        message = payload.get('message', '')

                        # Parse timestamp to epoch milliseconds
                        ts_dt = datetime.fromisoformat(ts.rstrip('Z'))
                        ts_ms = int(ts_dt.timestamp() * 1000)

                        user_messages.append({
                            'ts': ts,
                            'ts_ms': ts_ms,
                            'message': message,
                            'user_msg_index': user_message_index,
                            'total_msg_index': message_index
                        })
            except Exception:
                pass

    return token_data, user_messages, total_message_count


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


def format_time(ts: str) -> str:
    """Format timestamp for display."""
    try:
        dt = datetime.fromisoformat(ts.rstrip('Z'))
        return dt.strftime('%H:%M:%S')
    except:
        return ts


def format_date_short(ts: str) -> str:
    """Format date as 'Oct 04'."""
    try:
        dt = datetime.fromisoformat(ts.rstrip('Z'))
        return dt.strftime('%b %d')
    except:
        return ts


def format_date_full(ts: str) -> str:
    """Format date as '2025_10_04'."""
    try:
        dt = datetime.fromisoformat(ts.rstrip('Z'))
        return dt.strftime('%Y_%m_%d')
    except:
        return ts


def truncate_message(message: str, max_length: int = 400) -> str:
    """Truncate long messages with ... [omitted] in the middle."""
    if len(message) <= max_length:
        return message

    # Show equal parts from start and end
    half_length = (max_length - 25) // 2  # 25 chars for "\n\n ... [omitted] \n\n"
    start = message[:half_length].rstrip()
    end = message[-half_length:].lstrip()

    return f"{start}\n\n... [omitted]\n\n{end}"


def format_duration(seconds: float) -> str:
    """Format duration in (Xs), (Xm Ys), or (Xh Ym) - max 2 levels, no subseconds."""
    seconds = int(seconds)

    if seconds < 60:
        return f"({seconds}s)"

    minutes = seconds // 60
    secs = seconds % 60

    if minutes < 60:
        return f"({minutes}m {secs}s)"

    hours = minutes // 60
    mins = minutes % 60

    return f"({hours}h {mins}m)"


def list_sessions_in_last_hours(hours: float) -> None:
    """Print sessions under ~/.codex/sessions updated within the last N hours."""
    if not SESSIONS_ROOT.exists():
        print(f"Error: Sessions directory not found: {SESSIONS_ROOT}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now()
    cutoff_ts = (now - timedelta(hours=hours)).timestamp()

    recent_sessions: list[tuple[Path, float]] = []
    for jsonl_file in SESSIONS_ROOT.rglob('*.jsonl'):
        mtime = jsonl_file.stat().st_mtime
        if mtime >= cutoff_ts:
            recent_sessions.append((jsonl_file, mtime))

    if not recent_sessions:
        print(f"No session files modified within the last {hours:g} hour(s).")
        return

    recent_sessions.sort(key=lambda item: item[1], reverse=True)
    print(f"Active sessions within the last {hours:g} hour(s):")
    for index, (session_path, mtime) in enumerate(recent_sessions, 1):
        modified_dt = datetime.fromtimestamp(mtime)
        age = format_age(now - modified_dt)
        uuid = extract_uuid_from_name(session_path.name) or 'unknown'
        print(
            f"  {index}. {session_path} | uuid={uuid} | "
            f"modified {modified_dt.strftime('%Y-%m-%d %H:%M:%S')} ({age} ago)"
        )


def parse_flexible_datetime(date_str: str) -> datetime:
    """Parse flexible datetime string formats."""
    normalized = date_str.strip().replace('_', '-')

    # Try various formats
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2025-10-06 10:00:00
        '%Y-%m-%d %H:%M',     # 2025-10-06 10:00
        '%Y-%m-%d',           # 2025-10-06
    ]

    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue

    raise ValueError(f"Invalid datetime format: {date_str!r}. Expected formats: YYYY-MM-DD, YYYY-MM-DD HH:MM, or YYYY-MM-DD HH:MM:SS")


def find_sessions_since(since_str: str) -> list[Path]:
    """Find all sessions with active messages since the given datetime using DuckDB."""
    if not HAS_DUCKDB:
        print("Error: DuckDB is required for --since flag. Install with: pip install duckdb", file=sys.stderr)
        sys.exit(1)

    if not SESSIONS_ROOT.exists():
        print(f"Error: Sessions directory not found: {SESSIONS_ROOT}", file=sys.stderr)
        sys.exit(1)

    # Parse the since datetime
    since_dt = parse_flexible_datetime(since_str)
    since_timestamp = since_dt.isoformat()

    print(f"Finding sessions with messages since {since_dt.strftime('%Y-%m-%d %H:%M:%S')}...")

    # Get all JSONL files
    all_jsonl_files = list(SESSIONS_ROOT.rglob('*.jsonl'))

    if not all_jsonl_files:
        print(f"Error: No session files found in {SESSIONS_ROOT}", file=sys.stderr)
        sys.exit(1)

    # Use DuckDB to efficiently find sessions with messages in the date range
    conn = duckdb.connect(':memory:')

    matching_sessions = []

    for jsonl_file in all_jsonl_files:
        try:
            # Query for messages in this file that match the criteria
            query = f"""
            SELECT COUNT(*) as msg_count
            FROM read_json_auto('{jsonl_file}', format='newline_delimited')
            WHERE type = 'event_msg'
              AND timestamp >= '{since_timestamp}'
            """
            result = conn.execute(query).fetchone()

            if result and result[0] > 0:
                matching_sessions.append((jsonl_file, result[0]))
        except Exception:
            # Skip files that can't be read
            continue

    conn.close()

    if not matching_sessions:
        print(f"No sessions found with messages since {since_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        sys.exit(1)

    # Sort by modification time (oldest first for chronological plotting)
    matching_sessions.sort(key=lambda x: x[0].stat().st_mtime)

    print(f"Found {len(matching_sessions)} session(s) with messages since {since_dt.strftime('%Y-%m-%d %H:%M:%S')}:")
    for i, (session_path, msg_count) in enumerate(matching_sessions, 1):
        uuid = extract_uuid_from_name(session_path.name) or 'unknown'
        modified_dt = datetime.fromtimestamp(session_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {i}. {uuid} | {msg_count} messages | {session_path.name} (modified {modified_dt})")

    return [session_path for session_path, _ in matching_sessions]


def find_sessions_for_day(day_input: str) -> list[Path]:
    """Return one session file per agent UUID for the given day subdirectory."""
    normalized = day_input.strip().replace('_', '-')
    try:
        day_dt = datetime.strptime(normalized, '%Y-%m-%d')
    except ValueError as exc:
        raise ValueError(f"Invalid day format: {day_input!r}. Expected YYYY-MM-DD or YYYY_MM_DD") from exc

    day_dir = (
        SESSIONS_ROOT
        / f"{day_dt.year:04d}"
        / f"{day_dt.month:02d}"
        / f"{day_dt.day:02d}"
    )

    if not day_dir.exists():
        print(f"Error: No sessions directory found for {normalized}: {day_dir}", file=sys.stderr)
        sys.exit(1)

    uuid_to_entry: dict[str, tuple[Path, float]] = {}
    for jsonl_file in day_dir.rglob('*.jsonl'):
        uuid = extract_uuid_from_name(jsonl_file.name)
        if not uuid:
            continue
        mtime = jsonl_file.stat().st_mtime
        existing = uuid_to_entry.get(uuid)
        if existing is None or mtime > existing[1]:
            uuid_to_entry[uuid] = (jsonl_file, mtime)

    if not uuid_to_entry:
        print(f"Error: No session JSONL files found in {day_dir}", file=sys.stderr)
        sys.exit(1)

    ordered_entries = sorted(uuid_to_entry.items(), key=lambda item: item[1][1])
    print(
        f"Found {len(ordered_entries)} unique agent session(s) in {day_dir}:"
    )
    for index, (uuid, (session_path, mtime)) in enumerate(ordered_entries, 1):
        modified_dt = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {index}. {uuid} -> {session_path.name} (modified {modified_dt})")

    return [entry[1][0] for entry in ordered_entries]


def generate_html(token_data: list, user_messages: list, output_path: Path, session_file: Path, total_msg_count: int, message_based_x: bool = True) -> None:
    """Generate HTML chart with Chart.js showing tokens and user messages."""

    # Match user messages to token counts (find the closest token count at or after each message)
    user_scatter_context = []
    user_scatter_cumulative = []
    user_messages_with_context = []

    for msg in user_messages:
        # Find closest token count at or after this message timestamp
        closest_token = None
        for tok in token_data:
            if tok['ts_ms'] >= msg['ts_ms']:
                closest_token = tok
                break

        if closest_token:
            x_val = msg.get('total_msg_index', 0) if message_based_x else msg['ts_ms']
            user_scatter_context.append({
                'x': x_val,
                'y': closest_token['context_tokens'],
                'message': msg['message'],
                'user_msg_index': msg.get('user_msg_index', 0),
                'total_msg_index': msg.get('total_msg_index', 0),
                'x_time': msg['ts_ms'],
                'x_msg': msg.get('total_msg_index', 0)
            })
            user_scatter_cumulative.append({
                'x': x_val,
                'y': closest_token['cumulative_total'],
                'message': msg['message'],
                'user_msg_index': msg.get('user_msg_index', 0),
                'total_msg_index': msg.get('total_msg_index', 0),
                'x_time': msg['ts_ms'],
                'x_msg': msg.get('total_msg_index', 0)
            })
            user_messages_with_context.append({
                'ts': msg['ts'],
                'ts_ms': msg['ts_ms'],
                'message': msg['message'],
                'context_tokens': closest_token['context_tokens'],
                'cumulative_total': closest_token['cumulative_total'],
                'user_msg_index': msg.get('user_msg_index', 0),
                'total_msg_index': msg.get('total_msg_index', 0)
            })
        else:
            # If no later token count, use the last one
            if token_data:
                x_val = msg.get('total_msg_index', 0) if message_based_x else msg['ts_ms']
                user_scatter_context.append({
                    'x': x_val,
                    'y': token_data[-1]['context_tokens'],
                    'message': msg['message'],
                    'user_msg_index': msg.get('user_msg_index', 0),
                    'total_msg_index': msg.get('total_msg_index', 0),
                    'x_time': msg['ts_ms'],
                    'x_msg': msg.get('total_msg_index', 0)
                })
                user_scatter_cumulative.append({
                    'x': x_val,
                    'y': token_data[-1]['cumulative_total'],
                    'message': msg['message'],
                    'user_msg_index': msg.get('user_msg_index', 0),
                    'total_msg_index': msg.get('total_msg_index', 0),
                    'x_time': msg['ts_ms'],
                    'x_msg': msg.get('total_msg_index', 0)
                })
                user_messages_with_context.append({
                    'ts': msg['ts'],
                    'ts_ms': msg['ts_ms'],
                    'message': msg['message'],
                    'context_tokens': token_data[-1]['context_tokens'],
                    'cumulative_total': token_data[-1]['cumulative_total'],
                    'user_msg_index': msg.get('user_msg_index', 0),
                    'total_msg_index': msg.get('total_msg_index', 0)
                })

    # Prepare BOTH time-based and message-based data for toggle feature
    # Time-based data
    context_time_data = [{'x': pt['ts_ms'], 'y': pt['context_tokens']} for pt in token_data]
    cumulative_time_data = [{'x': pt['ts_ms'], 'y': pt['cumulative_total']} for pt in token_data]

    # Message-based data
    context_msg_data = [{'x': pt['message_index'], 'y': pt['context_tokens'], 'ts': pt['ts']} for pt in token_data]
    cumulative_msg_data = [{'x': pt['message_index'], 'y': pt['cumulative_total'], 'ts': pt['ts']} for pt in token_data]

    # Build complete index-to-timestamp map with interpolation
    index_to_ts = {}
    for pt in token_data:
        index_to_ts[pt['message_index']] = pt['ts']

    # Interpolate timestamps for all indices from 1 to total_msg_count
    if token_data:
        first_idx = min(pt['message_index'] for pt in token_data)
        last_idx = max(pt['message_index'] for pt in token_data)
        first_ts = min(pt['ts_ms'] for pt in token_data)
        last_ts = max(pt['ts_ms'] for pt in token_data)

        for idx in range(1, total_msg_count + 1):
            if idx not in index_to_ts:
                # Linear interpolation
                if last_idx > first_idx:
                    ratio = (idx - first_idx) / (last_idx - first_idx)
                    interpolated_ts_ms = first_ts + ratio * (last_ts - first_ts)
                    interpolated_dt = datetime.fromtimestamp(interpolated_ts_ms / 1000.0)
                    index_to_ts[idx] = interpolated_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    # Default dataset based on message_based_x
    context_chart_data = context_msg_data if message_based_x else context_time_data
    cumulative_chart_data = cumulative_msg_data if message_based_x else cumulative_time_data

    model_context_window = token_data[0]['model_context_window'] if token_data else 272000

    session_id = session_file.stem

    # Calculate date range for session
    if token_data:
        first_date = format_date_full(token_data[0]['ts'])
        last_date = format_date_full(token_data[-1]['ts'])
        if first_date == last_date:
            date_range = first_date
        else:
            date_range = f"{first_date} → {last_date}"
    else:
        date_range = ""

    # Calculate cost and execution time for each user message
    for i, msg in enumerate(user_messages_with_context):
        context_start = msg['context_tokens']
        time_start = msg['ts_ms']

        # Find context and time right before next user message
        if i < len(user_messages_with_context) - 1:
            # Get timestamp of next user message
            next_msg_ts = user_messages_with_context[i + 1]['ts_ms']
            # Find latest token_data before next message
            context_end = context_start
            time_end = time_start
            for tok in reversed(token_data):
                if tok['ts_ms'] < next_msg_ts:
                    context_end = tok['context_tokens']
                    time_end = tok['ts_ms']
                    break
        else:
            # Last user message - use final context and time
            context_end = token_data[-1]['context_tokens']
            time_end = token_data[-1]['ts_ms']

        cost = max(0, context_end - context_start)
        duration_seconds = (time_end - time_start) / 1000.0
        duration_str = format_duration(duration_seconds)

        msg['cost'] = cost
        msg['duration'] = duration_str

        # Add cost and duration to scatter data as well
        for scatter in user_scatter_context:
            if scatter.get('user_msg_index') == msg.get('user_msg_index'):
                scatter['cost'] = cost
                scatter['duration'] = duration_str
        for scatter in user_scatter_cumulative:
            if scatter.get('user_msg_index') == msg.get('user_msg_index'):
                scatter['cost'] = cost
                scatter['duration'] = duration_str

    # Generate chat message cards HTML (reversed order - most recent first)
    chat_cards_html = ""
    reversed_messages = list(reversed(user_messages_with_context))
    for msg in reversed_messages:
        user_msg_num = msg.get('user_msg_index', 0)
        total_msg_num = msg.get('total_msg_index', 0)
        truncated_msg = truncate_message(msg['message'])
        escaped_msg = escape_html(truncated_msg)
        time_str = format_time(msg['ts'])
        date_short = format_date_short(msg['ts'])
        date_full = format_date_full(msg['ts'])
        context_tokens = msg['context_tokens']
        cumulative_total = msg['cumulative_total']
        cost = msg.get('cost', 0)
        duration = msg.get('duration', '(0s)')
        # Remove closing paren, add date, re-add paren
        duration_with_date = duration.rstrip(')') + ' ' + date_short + ')'
        chat_cards_html += f"""
      <div class="message-card" data-index="{user_msg_num}" data-ts-ms="{msg['ts_ms']}" data-msg-index="{total_msg_num}" data-date-full="{date_full}" onclick="highlightMessage(this)">
        <div class="message-header">
          <div class="message-number">User Message #{user_msg_num} <span style="color: var(--accent); font-weight: 400;">{duration_with_date}</span></div>
          <div class="message-total">Message #{total_msg_num}</div>
        </div>
        <div class="message-text">{escaped_msg}</div>
        <div class="message-footer">
          <div class="message-context">Context: {context_tokens:,} ({cumulative_total:,}) | <span class="cost">Cost: {cost:,}</span></div>
          <div class="message-time">{time_str}</div>
        </div>
      </div>
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Context Window Usage - {session_id}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
  <style>
    :root {{
      --bg1: #0e1b4d;
      --bg2: #6b2bbf;
      --bg3: #a21caf;
      --card: rgba(20,24,45,0.9);
      --card-hover: rgba(30,34,55,0.95);
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #60a5fa;
      --shadow: 0 6px 18px rgba(0,0,0,0.35);
      --border: rgba(156,163,175,0.2);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 20px 20px 20px 20px;
      font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;
      color: var(--text);
      background: linear-gradient(135deg, var(--bg1) 0%, var(--bg2) 60%, var(--bg3) 100%);
      height: 100vh;
      overflow: hidden;
    }}
    .container {{ max-width: 1800px; margin: 0 auto; }}
    .header {{ text-align: center; margin-bottom: 20px; position: relative; }}
    .header h1 {{ margin: 0 0 8px; font-size: 28px; font-weight: 700; }}
    .header p {{ margin: 0; color: var(--muted); font-size: 14px; }}
    .chart-title .cost-suffix {{
      font-size: 12px;
      color: var(--muted);
      font-weight: 400;
      margin-left: 8px;
    }}

    .toggle-container {{
      position: absolute;
      right: 0;
      top: 50%;
      transform: translateY(-50%);
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .toggle-label {{
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .toggle-switch {{
      position: relative;
      width: 56px;
      height: 28px;
      background: rgba(30,34,55,0.7);
      border-radius: 14px;
      cursor: pointer;
      transition: background 0.3s ease;
    }}

    .toggle-switch.active {{
      background: var(--card);
    }}

    .toggle-slider {{
      position: absolute;
      top: 3px;
      left: 3px;
      width: 22px;
      height: 22px;
      background: white;
      border-radius: 50%;
      transition: transform 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
    }}

    .toggle-switch.active .toggle-slider {{
      transform: translateX(28px);
    }}

    .toggle-icon {{
      color: #4b5563;
      font-weight: bold;
      font-size: 12px;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(91px, 1fr));
      gap: 10px;
      margin-bottom: 20px;
    }}
    .stat-card {{
      background: var(--card);
      border-radius: 12px;
      padding: 12px;
      box-shadow: var(--shadow);
    }}
    .stat-title {{ font-size: 10px; color: var(--muted); letter-spacing: .08em; text-transform: uppercase; margin-bottom: 4px; }}
    .stat-value {{ font-size: 20px; font-weight: 700; color: var(--accent); }}

    .main-layout {{
      display: grid;
      grid-template-columns: 3fr 1fr;
      gap: 20px;
      align-items: start;
    }}

    .charts-container {{
      display: flex;
      flex-direction: column;
      gap: 20px;
      height: calc(100vh - 210px);
    }}

    .chart-section {{
      background: var(--card);
      border-radius: 12px;
      padding: 20px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(6px);
      flex: 1;
      display: flex;
      flex-direction: column;
    }}

    .chart-title {{
      font-size: 16px;
      font-weight: 600;
      color: var(--text);
      margin: 0 0 15px 0;
      text-align: center;
    }}

    .chart-wrap {{ position: relative; flex: 1; }}

    .chat-pane {{
      background: var(--card);
      border-radius: 12px;
      padding: 20px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(6px);
      height: calc(100vh - 210px);
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .chat-pane::-webkit-scrollbar {{
      width: 8px;
    }}
    .chat-pane::-webkit-scrollbar-track {{
      background: rgba(156,163,175,0.1);
      border-radius: 4px;
    }}
    .chat-pane::-webkit-scrollbar-thumb {{
      background: rgba(96,165,250,0.5);
      border-radius: 4px;
    }}
    .chat-pane::-webkit-scrollbar-thumb:hover {{
      background: rgba(96,165,250,0.7);
    }}

    .chat-header {{
      font-size: 16px;
      font-weight: 600;
      color: var(--text);
      margin: -20px -20px 12px -20px;
      padding: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: -20px;
      background: rgba(20,24,45,1);
      backdrop-filter: blur(10px);
      z-index: 10;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}

    .message-card {{
      background: rgba(30,34,55,0.7);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      transition: all 0.2s ease;
      cursor: pointer;
    }}

    .message-card:hover {{
      background: var(--card-hover);
      border-color: var(--accent);
      transform: translateX(-2px);
      box-shadow: 0 4px 12px rgba(96,165,250,0.2);
    }}

    .message-card.selected {{
      background: var(--card-hover);
      border: 2px solid #fbbf24;
      box-shadow: 0 0 20px rgba(251,191,36,0.4), 0 4px 12px rgba(96,165,250,0.3);
      transform: translateX(-2px);
    }}

    .message-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }}

    .message-number {{
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .message-total {{
      font-size: 11px;
      color: var(--accent);
      font-weight: 500;
    }}

    .message-text {{
      color: var(--text);
      font-size: 14px;
      line-height: 1.5;
      margin-bottom: 10px;
      white-space: pre-wrap;
      word-wrap: break-word;
    }}

    .message-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--border);
    }}

    .message-context {{
      font-size: 11px;
      color: var(--muted);
      font-weight: 500;
    }}

    .cost {{
      color: var(--muted);
      font-weight: 500;
    }}

    .message-time {{
      font-size: 12px;
      color: var(--accent);
      font-family: 'Monaco', 'Menlo', monospace;
    }}

    @media (max-width: 1200px) {{
      .main-layout {{
        grid-template-columns: 1fr;
      }}
      .chat-pane {{
        height: 400px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Context Window Usage Over Time</h1>
      <p>Session: {session_id} | {date_range}</p>
      <div class="toggle-container">
        <span class="toggle-label">Message based x-axis</span>
        <div id="toggleSwitch" class="toggle-switch {'active' if message_based_x else ''}" onclick="toggleXAxis()">
          <div class="toggle-slider">
            <span class="toggle-icon" id="toggleIcon">{'✓' if message_based_x else '✕'}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat-card">
        <div class="stat-title">Token Events</div>
        <div class="stat-value">{len(token_data):,}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">User Messages</div>
        <div class="stat-value">{len(user_messages):,}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Total Messages</div>
        <div class="stat-value">{total_msg_count:,}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Final Context</div>
        <div class="stat-value">{token_data[-1]['context_tokens']:,}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Total</div>
        <div class="stat-value">{token_data[-1]['cumulative_total']:,}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Model CW</div>
        <div class="stat-value">{model_context_window:,}</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Context Usage</div>
        <div class="stat-value">{(token_data[-1]['context_tokens'] / model_context_window * 100):.1f}%</div>
      </div>
    </div>

    <div class="main-layout">
      <div class="charts-container">
        <div class="chart-section">
          <h3 class="chart-title" id="contextChartTitle">Context Window Over Time</h3>
          <div class="chart-wrap">
            <canvas id="contextChart"></canvas>
          </div>
        </div>
        <div class="chart-section">
          <h3 class="chart-title" id="cumulativeChartTitle">Cumulative Total Tokens</h3>
          <div class="chart-wrap">
            <canvas id="cumulativeChart"></canvas>
          </div>
        </div>
      </div>

      <div class="chat-pane">
        <div class="chat-header">👤 User Messages</div>
{chat_cards_html}
      </div>
    </div>
  </div>

  <script>
    // Both time-based and message-based datasets
    const CONTEXT_TIME_DATA = {json.dumps(context_time_data)};
    const CUMULATIVE_TIME_DATA = {json.dumps(cumulative_time_data)};
    const CONTEXT_MSG_DATA = {json.dumps(context_msg_data)};
    const CUMULATIVE_MSG_DATA = {json.dumps(cumulative_msg_data)};

    const USER_MESSAGES_CONTEXT = {json.dumps(user_scatter_context)};
    const USER_MESSAGES_CUMULATIVE = {json.dumps(user_scatter_cumulative)};
    const MODEL_CONTEXT_WINDOW = {model_context_window};
    const INDEX_TO_TS = {json.dumps(index_to_ts)};

    // Current mode
    let MESSAGE_BASED_X = {'true' if message_based_x else 'false'};

    // Helper function to wrap text at a given character limit
    function wrapText(text, maxWidth) {{
      const words = text.split(' ');
      const lines = [];
      let currentLine = '';

      for (let word of words) {{
        const testLine = currentLine ? currentLine + ' ' + word : word;
        if (testLine.length > maxWidth && currentLine) {{
          lines.push(currentLine);
          currentLine = word;
        }} else {{
          currentLine = testLine;
        }}
      }}

      if (currentLine) {{
        lines.push(currentLine);
      }}

      return lines;
    }}

    // Helper to format timestamp from ISO string
    function formatTime(isoString) {{
      const date = new Date(isoString);
      return date.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit', hour12: false }});
    }}

    // X-axis config generator
    function getXAxisConfig(isMessageBased) {{
      if (isMessageBased) {{
        return {{
          type: 'linear',
          title: {{
            display: true,
            text: 'Time (message-based spacing)',
            color: '#9ca3af',
            font: {{ size: 14 }}
          }},
          ticks: {{
            color: '#9ca3af',
            maxTicksLimit: 20,
            autoSkip: true,
            callback: function(value) {{
              const idx = Math.round(value);
              const ts = INDEX_TO_TS[idx];
              if (ts) {{
                return formatTime(ts);
              }}
              return '';
            }}
          }},
          grid: {{ color: 'rgba(156,163,175,0.1)' }}
        }};
      }} else {{
        return {{
          type: 'time',
          time: {{
            unit: 'minute',
            displayFormats: {{
              minute: 'HH:mm',
              hour: 'HH:mm'
            }}
          }},
          title: {{
            display: true,
            text: 'Time',
            color: '#9ca3af',
            font: {{ size: 14 }}
          }},
          ticks: {{ color: '#9ca3af' }},
          grid: {{ color: 'rgba(156,163,175,0.1)' }}
        }};
      }}
    }}

    // Chart 1: Context Window Over Time
    const ctxContext = document.getElementById('contextChart').getContext('2d');
    const contextChart = new Chart(ctxContext, {{
      type: 'line',
      data: {{
        datasets: [
          {{
            label: 'Context Window Tokens',
            data: MESSAGE_BASED_X ? CONTEXT_MSG_DATA : CONTEXT_TIME_DATA,
            parsing: false,
            borderColor: '#60a5fa',
            backgroundColor: 'rgba(96,165,250,0.15)',
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 0,
            borderWidth: 2,
            fill: true,
            order: 2
          }},
          {{
            label: 'User Messages',
            data: USER_MESSAGES_CONTEXT,
            parsing: false,
            type: 'scatter',
            backgroundColor: '#fbbf24',
            borderColor: '#f59e0b',
            borderWidth: 2,
            pointRadius: 8,
            pointHoverRadius: 10,
            pointStyle: 'star',
            rotation: 0,
            order: 1
          }},
          {{
            label: 'Model Context Window Limit',
            data: (function() {{
              const data = MESSAGE_BASED_X ? CONTEXT_MSG_DATA : CONTEXT_TIME_DATA;
              return [
                {{ x: data[0].x, y: MODEL_CONTEXT_WINDOW }},
                {{ x: data[data.length - 1].x, y: MODEL_CONTEXT_WINDOW }}
              ];
            }})(),
            parsing: false,
            borderColor: '#ef4444',
            borderWidth: 2,
            borderDash: [10, 5],
            pointRadius: 0,
            fill: false,
            order: 3
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        onClick: (event, elements) => {{
          if (elements.length > 0 && elements[0].datasetIndex === 1) {{
            const dataPoint = elements[0];
            const data = USER_MESSAGES_CONTEXT[dataPoint.index];
            const userMsgIdx = data.user_msg_index;
            const card = document.querySelector('.message-card[data-index="' + userMsgIdx + '"]');
            if (card) {{
              card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
              setTimeout(() => highlightMessage(card), 300);
            }}
          }}
        }},
        interaction: {{
          mode: 'nearest',
          intersect: true
        }},
        scales: {{
          x: getXAxisConfig(MESSAGE_BASED_X),
          y: {{
            beginAtZero: true,
            title: {{
              display: true,
              text: 'Tokens',
              color: '#9ca3af',
              font: {{ size: 14 }}
            }},
            ticks: {{
              color: '#9ca3af',
              callback: function(value) {{
                return value.toLocaleString();
              }}
            }},
            grid: {{ color: 'rgba(156,163,175,0.1)' }}
          }}
        }},
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#e5e7eb', padding: 10, font: {{ size: 11 }} }}
          }},
          tooltip: {{
            backgroundColor: 'rgba(20,24,45,0.95)',
            titleColor: '#e5e7eb',
            bodyColor: '#e5e7eb',
            borderColor: '#60a5fa',
            borderWidth: 1,
            padding: 12,
            displayColors: false,
            callbacks: {{
              title: function(context) {{
                if (context[0].dataset.label === 'User Messages') {{
                  const raw = context[0].raw;
                  const userIdx = raw.user_msg_index || 0;
                  const totalIdx = raw.total_msg_index || 0;
                  const padding = '                    ';
                  return '👤 User Message (#' + userIdx + ')' + padding + 'message #' + totalIdx;
                }}
                return context[0].label;
              }},
              label: function(context) {{
                if (context.dataset.label === 'User Messages') {{
                  const msg = context.raw.message || '';
                  const cost = context.raw.cost || 0;
                  const wrapped = wrapText(msg, 60);
                  wrapped.push('', 'Cost: ' + cost.toLocaleString() + ' tokens');
                  return wrapped;
                }} else if (context.dataset.label === 'Context Window Tokens') {{
                  const value = context.parsed.y;
                  const percent = ((value / MODEL_CONTEXT_WINDOW) * 100).toFixed(2);
                  return context.dataset.label + ': ' + value.toLocaleString() + ' (' + percent + '%)';
                }} else {{
                  return context.dataset.label + ': ' + context.parsed.y.toLocaleString();
                }}
              }}
            }}
          }}
        }}
      }}
    }});

    // Chart 2: Cumulative Total Tokens
    const ctxCumulative = document.getElementById('cumulativeChart').getContext('2d');
    const cumulativeChart = new Chart(ctxCumulative, {{
      type: 'line',
      data: {{
        datasets: [
          {{
            label: 'Cumulative Total Tokens',
            data: MESSAGE_BASED_X ? CUMULATIVE_MSG_DATA : CUMULATIVE_TIME_DATA,
            parsing: false,
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139,92,246,0.15)',
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 0,
            borderWidth: 2,
            fill: true,
            order: 2
          }},
          {{
            label: 'User Messages',
            data: USER_MESSAGES_CUMULATIVE,
            parsing: false,
            type: 'scatter',
            backgroundColor: '#fbbf24',
            borderColor: '#f59e0b',
            borderWidth: 2,
            pointRadius: 8,
            pointHoverRadius: 10,
            pointStyle: 'star',
            rotation: 0,
            order: 1
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        onClick: (event, elements) => {{
          if (elements.length > 0 && elements[0].datasetIndex === 1) {{
            const dataPoint = elements[0];
            const data = USER_MESSAGES_CUMULATIVE[dataPoint.index];
            const userMsgIdx = data.user_msg_index;
            const card = document.querySelector('.message-card[data-index="' + userMsgIdx + '"]');
            if (card) {{
              card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
              setTimeout(() => highlightMessage(card), 300);
            }}
          }}
        }},
        interaction: {{
          mode: 'nearest',
          intersect: true
        }},
        scales: {{
          x: getXAxisConfig(MESSAGE_BASED_X),
          y: {{
            beginAtZero: true,
            title: {{
              display: true,
              text: 'Total Tokens',
              color: '#9ca3af',
              font: {{ size: 14 }}
            }},
            ticks: {{
              color: '#9ca3af',
              callback: function(value) {{
                return value.toLocaleString();
              }}
            }},
            grid: {{ color: 'rgba(156,163,175,0.1)' }}
          }}
        }},
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#e5e7eb', padding: 10, font: {{ size: 11 }} }}
          }},
          tooltip: {{
            backgroundColor: 'rgba(20,24,45,0.95)',
            titleColor: '#e5e7eb',
            bodyColor: '#e5e7eb',
            borderColor: '#8b5cf6',
            borderWidth: 1,
            padding: 12,
            displayColors: false,
            callbacks: {{
              title: function(context) {{
                if (context[0].dataset.label === 'User Messages') {{
                  const raw = context[0].raw;
                  const userIdx = raw.user_msg_index || 0;
                  const totalIdx = raw.total_msg_index || 0;
                  const padding = '                    ';
                  return '👤 User Message (#' + userIdx + ')' + padding + 'message #' + totalIdx;
                }}
                return context[0].label;
              }},
              label: function(context) {{
                if (context.dataset.label === 'User Messages') {{
                  const msg = context.raw.message || '';
                  const cost = context.raw.cost || 0;
                  const wrapped = wrapText(msg, 60);
                  wrapped.push('', 'Cost: ' + cost.toLocaleString() + ' tokens');
                  return wrapped;
                }} else {{
                  return context.dataset.label + ': ' + context.parsed.y.toLocaleString();
                }}
              }}
            }}
          }}
        }}
      }}
    }});

    // Toggle function to switch between message-based and time-based x-axis
    function toggleXAxis() {{
      // Check if vertical line exists before toggling
      const contextLineIndex = contextChart.data.datasets.findIndex(d => d.label === 'Selected Message');
      const cumulativeLineIndex = cumulativeChart.data.datasets.findIndex(d => d.label === 'Selected Message');

      let savedLineData = null;
      if (contextLineIndex >= 0) {{
        const lineDataset = contextChart.data.datasets[contextLineIndex];
        savedLineData = {{
          tsMs: lineDataset.tsMs,
          msgIndex: lineDataset.msgIndex
        }};
        // Remove lines from both charts
        contextChart.data.datasets.splice(contextLineIndex, 1);
        cumulativeChart.data.datasets.splice(cumulativeLineIndex, 1);
      }}

      // Toggle mode
      MESSAGE_BASED_X = !MESSAGE_BASED_X;
      const toggleSwitch = document.getElementById('toggleSwitch');
      const toggleIcon = document.getElementById('toggleIcon');

      if (MESSAGE_BASED_X) {{
        toggleSwitch.classList.add('active');
        toggleIcon.textContent = '✓';
      }} else {{
        toggleSwitch.classList.remove('active');
        toggleIcon.textContent = '✕';
      }}

      // Update context chart
      const contextData = MESSAGE_BASED_X ? CONTEXT_MSG_DATA : CONTEXT_TIME_DATA;
      const userMsgContext = USER_MESSAGES_CONTEXT.map(pt => ({{
        ...pt,
        x: MESSAGE_BASED_X ? pt.x_msg : pt.x_time
      }}));

      contextChart.data.datasets[0].data = contextData;
      contextChart.data.datasets[1].data = userMsgContext;
      contextChart.data.datasets[2].data = [
        {{ x: contextData[0].x, y: MODEL_CONTEXT_WINDOW }},
        {{ x: contextData[contextData.length - 1].x, y: MODEL_CONTEXT_WINDOW }}
      ];
      contextChart.options.scales.x = getXAxisConfig(MESSAGE_BASED_X);
      contextChart.update('none');

      // Update cumulative chart
      const cumulativeData = MESSAGE_BASED_X ? CUMULATIVE_MSG_DATA : CUMULATIVE_TIME_DATA;
      const userMsgCumulative = USER_MESSAGES_CUMULATIVE.map(pt => ({{
        ...pt,
        x: MESSAGE_BASED_X ? pt.x_msg : pt.x_time
      }}));

      cumulativeChart.data.datasets[0].data = cumulativeData;
      cumulativeChart.data.datasets[1].data = userMsgCumulative;
      cumulativeChart.options.scales.x = getXAxisConfig(MESSAGE_BASED_X);
      cumulativeChart.update('none');

      // Redraw vertical line if it existed
      if (savedLineData) {{
        const xPos = MESSAGE_BASED_X ? savedLineData.msgIndex : savedLineData.tsMs;
        const contextYMax = Math.max(...CONTEXT_MSG_DATA.map(d => d.y), ...CONTEXT_TIME_DATA.map(d => d.y), MODEL_CONTEXT_WINDOW);
        const cumulativeYMax = Math.max(...CUMULATIVE_MSG_DATA.map(d => d.y), ...CUMULATIVE_TIME_DATA.map(d => d.y));

        contextChart.data.datasets.push({{
          label: 'Selected Message',
          data: [{{ x: xPos, y: 0 }}, {{ x: xPos, y: contextYMax }}],
          type: 'line',
          borderColor: '#fbbf24',
          borderWidth: 2,
          borderDash: [8, 4],
          pointRadius: 0,
          fill: false,
          order: 0,
          tsMs: savedLineData.tsMs,
          msgIndex: savedLineData.msgIndex
        }});

        cumulativeChart.data.datasets.push({{
          label: 'Selected Message',
          data: [{{ x: xPos, y: 0 }}, {{ x: xPos, y: cumulativeYMax }}],
          type: 'line',
          borderColor: '#fbbf24',
          borderWidth: 2,
          borderDash: [8, 4],
          pointRadius: 0,
          fill: false,
          order: 0,
          tsMs: savedLineData.tsMs,
          msgIndex: savedLineData.msgIndex
        }});

        contextChart.update('none');
        cumulativeChart.update('none');
      }}
    }}

    // Highlight message function - draws vertical line on both charts
    function highlightMessage(cardElement) {{
      // Remove selected class from all cards
      document.querySelectorAll('.message-card').forEach(card => {{
        card.classList.remove('selected');
      }});

      // Add selected class to clicked card
      cardElement.classList.add('selected');

      const tsMs = parseInt(cardElement.dataset.tsMs);
      const msgIndex = parseInt(cardElement.dataset.msgIndex);

      // Get cost, duration, and date from card data
      const userMsgNum = parseInt(cardElement.dataset.index);
      const costElement = cardElement.querySelector('.cost');
      const costText = costElement ? costElement.textContent.replace('Cost: ', '').trim() : '0';
      const dateFull = cardElement.dataset.dateFull || '';

      // Extract duration from card header (without date)
      const msgNumberElement = cardElement.querySelector('.message-number');
      const fullText = msgNumberElement ? msgNumberElement.textContent : '';
      const durationMatch = fullText.match(/\\(([^)]+)\\)/);
      let duration = durationMatch ? durationMatch[1] : '0s';
      // Remove date part from duration (e.g., "4m 22s Oct 04" -> "4m 22s")
      duration = duration.split(' ').slice(0, 2).join(' ');

      // Update chart titles with cost, duration, and date
      const contextTitle = document.getElementById('contextChartTitle');
      const cumulativeTitle = document.getElementById('cumulativeChartTitle');
      const costSuffix = '<span class="cost-suffix">• User Message #' + userMsgNum + ' Cost: ' + costText + ' tokens (' + duration + ' ' + dateFull + ')</span>';

      contextTitle.innerHTML = 'Context Window Over Time ' + costSuffix;
      cumulativeTitle.innerHTML = 'Cumulative Total Tokens ' + costSuffix;

      // Determine x position based on current mode
      const xPos = MESSAGE_BASED_X ? msgIndex : tsMs;

      // Find y-axis ranges for both charts
      const contextYMax = Math.max(...CONTEXT_MSG_DATA.map(d => d.y), ...CONTEXT_TIME_DATA.map(d => d.y), MODEL_CONTEXT_WINDOW);
      const cumulativeYMax = Math.max(...CUMULATIVE_MSG_DATA.map(d => d.y), ...CUMULATIVE_TIME_DATA.map(d => d.y));

      // Update or add vertical line dataset to context chart
      const contextLineIndex = contextChart.data.datasets.findIndex(d => d.label === 'Selected Message');
      const contextLineData = [
        {{ x: xPos, y: 0 }},
        {{ x: xPos, y: contextYMax }}
      ];

      if (contextLineIndex >= 0) {{
        contextChart.data.datasets[contextLineIndex].data = contextLineData;
        contextChart.data.datasets[contextLineIndex].tsMs = tsMs;
        contextChart.data.datasets[contextLineIndex].msgIndex = msgIndex;
      }} else {{
        const newDataset = {{
          label: 'Selected Message',
          data: contextLineData,
          type: 'line',
          borderColor: '#fbbf24',
          borderWidth: 2,
          borderDash: [8, 4],
          pointRadius: 0,
          fill: false,
          order: 0,
          tsMs: tsMs,
          msgIndex: msgIndex
        }};
        contextChart.data.datasets.push(newDataset);
      }}

      // Update or add vertical line dataset to cumulative chart
      const cumulativeLineIndex = cumulativeChart.data.datasets.findIndex(d => d.label === 'Selected Message');
      const cumulativeLineData = [
        {{ x: xPos, y: 0 }},
        {{ x: xPos, y: cumulativeYMax }}
      ];

      if (cumulativeLineIndex >= 0) {{
        cumulativeChart.data.datasets[cumulativeLineIndex].data = cumulativeLineData;
        cumulativeChart.data.datasets[cumulativeLineIndex].tsMs = tsMs;
        cumulativeChart.data.datasets[cumulativeLineIndex].msgIndex = msgIndex;
      }} else {{
        const newDataset = {{
          label: 'Selected Message',
          data: cumulativeLineData,
          type: 'line',
          borderColor: '#fbbf24',
          borderWidth: 2,
          borderDash: [8, 4],
          pointRadius: 0,
          fill: false,
          order: 0,
          tsMs: tsMs,
          msgIndex: msgIndex
        }};
        cumulativeChart.data.datasets.push(newDataset);
      }}

      contextChart.update();
      cumulativeChart.update();
    }}
  </script>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


def parse_args():
    """Parse command line arguments."""
    example_uuid = '0199aa4a-4aaa-7a71-ab74-320df9983ce1'
    example_file = '/Users/sotola/.codex/sessions/2025/10/03/rollout-2025-10-03T20-36-59-0199aa4a-4aaa-7a71-ab74-320df9983ce1.jsonl'

    parser = argparse.ArgumentParser(
        description='Generate context window usage charts for Codex session JSONL files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Example usage:
  python context_window_chart_v5.py {example_uuid}
  python context_window_chart_v5.py {example_file}
  python context_window_chart_v5.py --latest 5
  python context_window_chart_v5.py --since '2025-10-06'
  python context_window_chart_v5.py --since '2025-10-06 10:00:00'

Charts are always generated and auto-opened.
        """
    )

    parser.add_argument('session_file', nargs='?', help='Path to session JSONL file or UUID to search for')
    parser.add_argument('--latest', type=int, metavar='N', help='Analyze the latest N sessions from ~/.codex/sessions')
    parser.add_argument('--hours', type=float, metavar='H', help='List sessions touched within the last H hours')
    parser.add_argument('--day', type=str, metavar='YYYY-MM-DD',
                        help='Analyze all agent sessions for the given day (YYYY-MM-DD or YYYY_MM_DD)')
    parser.add_argument('--since', type=str, metavar='DATETIME',
                        help='Analyze sessions with messages since given datetime (YYYY-MM-DD, YYYY_MM_DD, or YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--time-based-x', action='store_true', help='Use time-based x-axis instead of message-based (default is message-based)')
    parser.add_argument('--output-dir', default='/Users/sotola/ai/generated_artifacts',
                        help='Output directory for HTML files (default: %(default)s)')

    # If no arguments provided, print help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    selection_flags = {
        'session_file or UUID': bool(args.session_file),
        '--latest': args.latest is not None,
        '--hours': args.hours is not None,
        '--day': args.day is not None,
        '--since': args.since is not None,
    }

    active_options = [name for name, is_set in selection_flags.items() if is_set]

    if not active_options:
        parser.error('Provide one of: session_file/UUID, --latest N, --hours H, --day YYYY-MM-DD, or --since DATETIME')

    if len(active_options) > 1:
        parser.error(f"Options {', '.join(active_options)} cannot be combined; choose exactly one")

    if args.latest is not None and args.latest <= 0:
        parser.error('--latest requires a positive integer')

    if args.hours is not None and args.hours <= 0:
        parser.error('--hours requires a positive value')

    return args


def find_sessions_by_uuid(uuid: str) -> list[Path]:
    """Find session files matching the given UUID."""
    if not SESSIONS_ROOT.exists():
        print(f"Error: Sessions directory not found: {SESSIONS_ROOT}", file=sys.stderr)
        sys.exit(1)

    # Find all JSONL files containing the UUID
    matching_sessions = []
    for jsonl_file in SESSIONS_ROOT.rglob('*.jsonl'):
        if uuid.lower() in jsonl_file.name.lower():
            matching_sessions.append(jsonl_file)

    if not matching_sessions:
        print(f"Error: No session files found matching UUID: {uuid}", file=sys.stderr)
        sys.exit(1)

    # Sort by modification time (most recent first)
    matching_sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    print(f"Found {len(matching_sessions)} session(s) matching UUID '{uuid}':")
    for i, session in enumerate(matching_sessions, 1):
        print(f"  {i}. {session}")

    return matching_sessions


def find_latest_sessions(n: int) -> list[Path]:
    """Find the latest N session files from ~/.codex/sessions."""
    if not SESSIONS_ROOT.exists():
        print(f"Error: Sessions directory not found: {SESSIONS_ROOT}", file=sys.stderr)
        sys.exit(1)

    # Find all JSONL files
    all_sessions = list(SESSIONS_ROOT.rglob('*.jsonl'))

    if not all_sessions:
        print(f"Error: No session files found in {SESSIONS_ROOT}", file=sys.stderr)
        sys.exit(1)

    # Sort by modification time (most recent first)
    all_sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Return the latest N
    latest = all_sessions[:n]

    print(f"Found {len(all_sessions)} total sessions, using latest {len(latest)}:")
    for i, session in enumerate(latest, 1):
        print(f"  {i}. {session.name}")

    return latest


def main():
    """Main execution."""
    args = parse_args()

    if args.hours is not None:
        list_sessions_in_last_hours(args.hours)
        return

    # Determine which sessions to analyze
    if args.since:
        session_files = find_sessions_since(args.since)
    elif args.day:
        session_files = find_sessions_for_day(args.day)
    elif args.latest is not None:
        session_files = find_latest_sessions(args.latest)
        # Sort chronologically (oldest first) for plotting
        session_files.sort(key=lambda p: p.stat().st_mtime)
    else:
        # Check if input is a UUID or a file path
        input_str = args.session_file
        session_file_path = Path(input_str)

        # If it's not an existing file, treat it as UUID and search for it
        if not session_file_path.exists():
            # Looks like a UUID - search for matching files
            session_files = find_sessions_by_uuid(input_str)
            # Sort chronologically (oldest first) for plotting
            session_files.sort(key=lambda p: p.stat().st_mtime)
        else:
            # It's a valid file path
            session_files = [session_file_path]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_charts = []
    total_token_events = 0
    total_user_messages = 0

    # Process each session individually
    for session_file in session_files:
        print(f"\nAnalyzing session: {session_file.name}")
        token_data, user_messages, total_msg_count = extract_session_data(session_file)
        print(f"  Found {len(token_data)} token_count events")
        print(f"  Found {len(user_messages)} user messages")
        print(f"  Total messages in session: {total_msg_count}")

        total_token_events += len(token_data)
        total_user_messages += len(user_messages)

        if not token_data:
            print(f"  Skipping (no token data)")
            continue

        # Always generate chart
        output_path = output_dir / f"context_window_chart_{session_file.stem}.html"
        message_based = not args.time_based_x
        generate_html(token_data, user_messages, output_path, session_file, total_msg_count, message_based)
        print(f"  Chart generated: {output_path}")
        generated_charts.append(output_path)

        # Show stats for this session
        print(f"  Stats:")
        print(f"    First timestamp: {token_data[0]['ts']}")
        print(f"    Last timestamp:  {token_data[-1]['ts']}")
        print(f"    Final context:   {token_data[-1]['context_tokens']:,} tokens")
        print(f"    Cumulative total: {token_data[-1]['cumulative_total']:,} tokens")
        print(f"    Context usage: {(token_data[-1]['context_tokens'] / token_data[0]['model_context_window'] * 100):.1f}%")

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total sessions analyzed: {len(session_files)}")
    print(f"  Total token events: {total_token_events:,}")
    print(f"  Total user messages: {total_user_messages:,}")
    if generated_charts:
        print(f"  Charts generated: {len(generated_charts)}")

    # Always auto-open all charts
    if generated_charts:
        print(f"\nOpening {len(generated_charts)} chart(s)...")
        for chart_path in generated_charts:
            try:
                subprocess.run(['open', str(chart_path)], check=False)
            except Exception as e:
                print(f"Warning: Could not auto-open {chart_path}: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()
