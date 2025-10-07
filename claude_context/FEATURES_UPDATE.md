# Feature Update: Vertical Crosshair & Enhanced Tooltips

## Added Features (v1.2.0)

### 1. Vertical Crosshair Line ✨
When you click on a user message in the sidebar, a **yellow dashed vertical line** appears on both charts showing exactly when that message occurred.

**Benefits:**
- Visually correlate messages with token usage
- See the exact timing of each interaction
- Understand how context grows after each message

**How it works:**
- Line persists when toggling between time-based and message-based views
- Automatically adjusts position based on current x-axis mode
- Spans full height of both charts for easy comparison

### 2. Enhanced Chart Titles 📊
Clicking a message updates the chart titles to show:
- User message number
- Token cost for that interaction
- Duration of the interaction
- Date of the message

**Example:**
```
Context Window Over Time • User Message #5 Cost: 797 tokens (3m 4s 2025_10_07)
```

### 3. Improved Tooltips
Hover over user message stars (⭐) on the chart to see:
- Full message text (wrapped for readability)
- Token cost calculation
- Context window size at that point

## Code Changes

### Before (Simple highlight)
```javascript
function highlightMessage(cardElement) {
  document.querySelectorAll('.message-card').forEach(card => card.classList.remove('selected'));
  cardElement.classList.add('selected');
}
```

### After (Full feature set)
```javascript
function highlightMessage(cardElement) {
  // 1. Highlight the card
  document.querySelectorAll('.message-card').forEach(card => card.classList.remove('selected'));
  cardElement.classList.add('selected');

  // 2. Extract message metadata
  const tsMs = parseInt(cardElement.dataset.tsMs);
  const msgIndex = parseInt(cardElement.dataset.msgIndex);
  const cost = ...;
  const duration = ...;

  // 3. Update chart titles
  contextTitle.innerHTML = 'Context Window Over Time ' + costSuffix;

  // 4. Draw vertical line on both charts
  const verticalLine = {
    label: 'Selected Message',
    data: [{ x: xPos, y: 0 }, { x: xPos, y: yMax }],
    borderColor: '#fbbf24',
    borderDash: [8, 4],
    ...
  };
  contextChart.data.datasets.push(verticalLine);
  contextChart.update();
}
```

### Toggle Function Enhancement
The toggle function now:
1. **Saves** vertical line position before mode change
2. **Removes** line temporarily during transition
3. **Redraws** line in correct position for new mode

This ensures the crosshair stays visible when switching between time-based and message-based views.

## CSS Additions

```css
.chart-title .cost-suffix {
  font-size: 12px;
  color: var(--muted);
  font-weight: 400;
  margin-left: 8px;
}
```

## Feature Parity with Codex Version ✅

The Claude version now has **complete feature parity** with the Codex version:

| Feature | Codex | Claude (Before) | Claude (After) |
|---------|-------|-----------------|----------------|
| Vertical crosshair | ✅ | ❌ | ✅ |
| Chart title updates | ✅ | ❌ | ✅ |
| Hover tooltips | ✅ | ✅ | ✅ |
| Click-to-scroll | ✅ | ✅ | ✅ |
| Message filtering | ❌ | ✅ | ✅ |
| Cache tracking | ❌ | ✅ | ✅ |

## Usage

1. **Click** any user message in the sidebar
2. **See** the yellow vertical line appear on both charts
3. **Read** the updated chart title showing cost and duration
4. **Toggle** between time/message view - line stays visible
5. **Click** another message to move the line

## Visual Example

```
Before click:
Context Window Over Time

After clicking User Message #4:
Context Window Over Time • User Message #4 Cost: 797 tokens (3m 4s 2025_10_07)
                          └─ Yellow crosshair line appears ─┘
```

## Implementation Notes

- Line is added as a dataset to both charts
- Uses Chart.js `type: 'line'` with `borderDash` for dashed effect
- Stored with `tsMs` and `msgIndex` properties for toggle persistence
- CSS suffix styling matches Codex version exactly

## Future Enhancements

Possible improvements:
- [ ] Highlight corresponding star on chart when hovering message card
- [ ] Show mini-chart preview in message card
- [ ] Export selected message cost data to CSV
- [ ] Keyboard shortcuts for navigating messages (↑/↓ arrows)
