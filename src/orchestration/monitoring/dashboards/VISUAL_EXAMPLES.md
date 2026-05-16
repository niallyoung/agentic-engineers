# Dashboard Visual Examples & Screenshots

**Purpose**: Document expected visual appearance of new dashboard panels

**Status**: Design specification (screenshots pending deployment)

---

## Panel 12: Token Throughput (Input/Output/Cached)

### Visual Type
Multi-line timeseries chart with legend

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Token Throughput (input/output/cached)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Tokens/s                                                   │
│  │                                                          │
│  │      ╱╲      ╱╲      ╱╲                                 │
│  │     ╱  ╲    ╱  ╲    ╱  ╲                                │
│  │    ╱    ╲  ╱    ╲  ╱    ╲                               │
│  │───────────────────────────────────────────────────────  │
│  │                                                          │
│  └─────────────────────────────────────────────────────────┘
│  ┌─────────────────────────────────────────────────────────┐
│  │ Input Tokens/s    Mean: 2,500  Max: 4,200              │
│  │ Output Tokens/s   Mean: 1,500  Max: 2,800              │
│  │ Cached Tokens/s   Mean: 800    Max: 1,500              │
│  └─────────────────────────────────────────────────────────┘
```

### Color Coding
- Blue line: Input tokens
- Orange line: Output tokens
- Green line: Cached tokens

### Interpretation
- **Steady lines**: Consistent token consumption
- **Spikes**: Sudden increase in token usage
- **Gaps**: No activity during that period
- **Cached tokens**: Indicates prompt caching working

### What to Watch
- Input/output ratio (typically 1:0.5 to 1:1)
- Cached token growth (indicates caching effectiveness)
- Sudden spikes (may indicate unusual activity)

---

## Panel 13: Token Usage by Model

### Visual Type
Pie chart with percentage labels

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Token Usage by Model                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│              ╱─────────╲                                    │
│           ╱──           ──╲                                 │
│         ╱                   ╲                               │
│        │  Haiku 25%         │                              │
│        │  Sonnet 50%        │                              │
│        │  Opus 25%          │                              │
│         ╲                   ╱                               │
│           ╲──           ──╱                                 │
│              ╲─────────╱                                    │
│                                                              │
│  Legend:                                                    │
│  ■ Haiku (25%)                                             │
│  ■ Sonnet (50%)                                            │
│  ■ Opus (25%)                                              │
└─────────────────────────────────────────────────────────────┘
```

### Color Coding
- Blue: Haiku (budget-conscious)
- Green: Sonnet (balanced)
- Purple: Opus (high-capability)

### Interpretation
- **Haiku-heavy (>40%)**: Cost-optimized routing
- **Sonnet-heavy (>50%)**: Balanced approach
- **Opus-heavy (>30%)**: Complex tasks or over-engineering

### What to Watch
- Haiku percentage (should be >20% for cost optimization)
- Opus percentage (should be <30% unless complex tasks)
- Changes in distribution (indicates routing changes)

---

## Panel 14: Tokens per Task (Histogram)

### Visual Type
Multi-line timeseries showing percentiles

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Tokens per Task (histogram)                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Tokens                                                     │
│  │                                                          │
│  │  15K ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ P99
│  │  10K ─────────────────────────────────────────────── P95
│  │   7K ───────────────────────────────────────────── P75
│  │   5K ─────────────────────────────────────────── P50
│  │   2K ───────────────────────────────────────── P25
│  │     └──────────────────────────────────────────────────
│  │                                                          │
│  └─────────────────────────────────────────────────────────┘
│  ┌─────────────────────────────────────────────────────────┐
│  │ P25: 2,000   P50: 5,000   P75: 7,000   P95: 10,000     │
│  │ P99: 15,000  Mean: 6,200  Max: 18,500                  │
│  └─────────────────────────────────────────────────────────┘
```

### Color Coding
- Red: P99 (99th percentile)
- Orange: P95
- Yellow: P75
- Green: P50
- Blue: P25

### Interpretation
- **Narrow band**: Consistent task complexity
- **Wide band**: Varied task complexity
- **High P99**: Outlier tasks consuming many tokens
- **Low P25**: Some very simple tasks

### What to Watch
- P99 value (identify expensive outliers)
- P50 value (typical task complexity)
- Trend over time (increasing = more complex tasks)

---

## Panel 15: Cache Hit Rate

### Visual Type
Gauge with color-coded thresholds

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Cache Hit Rate                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                    ╱───────╲                                │
│                 ╱─────────────╲                             │
│               ╱─────────────────╲                           │
│              │                   │                          │
│              │      35%          │                          │
│              │                   │                          │
│              │   ▲               │                          │
│               ╲─────────────────╱                           │
│                 ╲─────────────╱                             │
│                    ╲───────╱                                │
│                                                              │
│  0%          20%         40%         60%        100%        │
│  🟢 Green    🟡 Yellow   🟢 Green                           │
│  (poor)      (moderate)  (excellent)                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Color Coding
- 🔴 Red: 0-20% (poor caching)
- 🟡 Yellow: 20-40% (moderate caching)
- 🟢 Green: 40%+ (excellent caching)

### Interpretation
- **Green (40%+)**: Prompt caching working well
- **Yellow (20-40%)**: Moderate caching, room for improvement
- **Red (<20%)**: Poor caching, needs optimization

### What to Watch
- Gauge position (should be in green)
- Trend over time (should increase with caching improvements)
- Sudden drops (may indicate caching disabled)

---

## Panel 16: Daily Cost (USD)

### Visual Type
Large stat card with color background

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Daily Cost (USD)                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                                                              │
│                      $245.50                                │
│                                                              │
│                                                              │
│  Background Color:                                          │
│  🟢 Green ($0-100)                                          │
│  🟡 Yellow ($100-500)  ← Current value                     │
│  🔴 Red (>$500)                                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Color Coding
- 🟢 Green: $0-100 (low cost)
- 🟡 Yellow: $100-500 (moderate cost)
- 🔴 Red: >$500 (high cost)

### Interpretation
- **Green**: Daily cost within budget
- **Yellow**: Moderate spending, monitor closely
- **Red**: High spending, investigate and optimize

### What to Watch
- Threshold changes (indicates spending changes)
- Trend over days (should be stable or decreasing)
- Sudden spikes (may indicate unusual activity)

---

## Panel 17: Cost by Role

### Visual Type
Pie chart with percentage labels

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Cost by Role                                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│           ╱──────────────╲                                  │
│        ╱──                  ──╲                             │
│      ╱                          ╲                           │
│    │  Engineer 35%              │                          │
│    │  Senior Eng 40%            │                          │
│    │  Lead Eng 15%              │                          │
│    │  Principal 5%              │                          │
│    │  Quality 3%                │                          │
│    │  Security 2%               │                          │
│      ╲                          ╱                           │
│        ╲──                  ──╱                             │
│           ╲──────────────╱                                  │
│                                                              │
│  Legend:                                                    │
│  ■ Engineer (35%)                                           │
│  ■ Senior Engineer (40%)                                    │
│  ■ Lead Engineer (15%)                                      │
│  ■ Principal Engineer (5%)                                  │
│  ■ Quality Engineer (3%)                                    │
│  ■ Security Engineer (2%)                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Color Coding
- Blue: Engineer
- Green: Senior Engineer
- Orange: Lead Engineer
- Red: Principal Engineer
- Purple: Quality Engineer
- Gray: Security Engineer

### Interpretation
- **Engineer-heavy (>40%)**: Good cost optimization
- **Senior Engineer-heavy (>40%)**: Balanced approach
- **Principal Engineer-heavy (>20%)**: Complex/architectural work
- **Quality Engineer-heavy (>10%)**: Extensive review/testing

### What to Watch
- Engineer percentage (should be >30% for cost optimization)
- Principal percentage (should be <15% unless architectural work)
- Changes in distribution (indicates workload changes)

---

## Panel 18: Cost by Model

### Visual Type
Pie chart with percentage labels

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Cost by Model                                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│              ╱─────────╲                                    │
│           ╱──           ──╲                                 │
│         ╱                   ╲                               │
│        │  Haiku 20%         │                              │
│        │  Sonnet 45%        │                              │
│        │  Opus 35%          │                              │
│         ╲                   ╱                               │
│           ╲──           ──╱                                 │
│              ╲─────────╱                                    │
│                                                              │
│  Legend:                                                    │
│  ■ Haiku (20%)   - $0.80/$4.00 per 1M tokens              │
│  ■ Sonnet (45%)  - $3.00/$15.00 per 1M tokens             │
│  ■ Opus (35%)    - $15.00/$75.00 per 1M tokens            │
│                                                              │
│  Cost Breakdown:                                            │
│  Haiku: $49.00 (20%)                                        │
│  Sonnet: $110.25 (45%)                                      │
│  Opus: $85.75 (35%)                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Color Coding
- Blue: Haiku (budget-conscious)
- Green: Sonnet (balanced)
- Red: Opus (expensive)

### Interpretation
- **Haiku-heavy (>30%)**: Cost-optimized
- **Sonnet-heavy (>40%)**: Balanced approach
- **Opus-heavy (>40%)**: Complex tasks or over-engineering

### What to Watch
- Opus percentage (should be <40% unless complex work)
- Haiku percentage (should be >15% for cost optimization)
- Cost per model (identify which models are expensive)

---

## Panel 19: Cost per Task (Histogram)

### Visual Type
Multi-line timeseries showing percentiles

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Cost per Task (histogram)                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Cost (USD)                                                 │
│  │                                                          │
│  │  $50  ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ P99
│  │  $35  ─────────────────────────────────────────────── P95
│  │  $20  ───────────────────────────────────────────── P75
│  │  $10  ─────────────────────────────────────────── P50
│  │  $2   ───────────────────────────────────────── P25
│  │     └──────────────────────────────────────────────────
│  │                                                          │
│  └─────────────────────────────────────────────────────────┘
│  ┌─────────────────────────────────────────────────────────┐
│  │ P25: $2.00   P50: $10.00   P75: $20.00   P95: $35.00   │
│  │ P99: $50.00  Mean: $12.50  Max: $65.00                 │
│  └─────────────────────────────────────────────────────────┘
```

### Color Coding
- Red: P99 (expensive outliers)
- Orange: P95
- Yellow: P75
- Green: P50
- Blue: P25

### Interpretation
- **Narrow band**: Consistent task costs
- **Wide band**: Varied task costs
- **High P99**: Expensive outlier tasks
- **Low P25**: Some very cheap tasks

### What to Watch
- P99 value (identify expensive outliers)
- P50 value (typical task cost)
- Trend over time (increasing = more expensive tasks)

---

## Panel 20: Cost Trend (7 days)

### Visual Type
Area chart with filled region

### Expected Appearance
```
┌─────────────────────────────────────────────────────────────┐
│ Cost Trend (7 days)                                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Daily Cost (USD)                                           │
│  │                                                          │
│  │  $300 ╱╲                                                │
│  │      ╱  ╲      ╱╲                                       │
│  │  $250╱    ╲    ╱  ╲      ╱╲                             │
│  │    ╱      ╲  ╱    ╲    ╱  ╲                             │
│  │  $200─────╲╱──────╲──╱────╲╱──                          │
│  │          ╱╲       ╱╲      ╱╲                            │
│  │  $150  ╱  ╲     ╱  ╲    ╱  ╲                            │
│  │       ╱    ╲   ╱    ╲  ╱    ╲                           │
│  │  $100─────────────────────────                          │
│  │                                                          │
│  │  Mon  Tue  Wed  Thu  Fri  Sat  Sun                      │
│  │                                                          │
│  └─────────────────────────────────────────────────────────┘
│  ┌─────────────────────────────────────────────────────────┐
│  │ Min: $150   Mean: $220   Max: $300                      │
│  │ Trend: ↑ Upward (increasing costs)                      │
│  └─────────────────────────────────────────────────────────┘
```

### Color Coding
- Blue area: Daily cost
- Blue line: Cost trend

### Interpretation
- **Upward trend**: Costs increasing (investigate)
- **Downward trend**: Cost optimization working
- **Flat trend**: Stable costs
- **Spikes**: Unusual high-cost days

### What to Watch
- Overall trend (should be stable or decreasing)
- Weekly patterns (e.g., higher on weekdays)
- Sudden spikes (may indicate unusual activity)
- Comparison to budget

---

## Dashboard Refresh Behavior

### Refresh Rate: 30 seconds

**Visual Behavior**:
```
Time: 14:00:00 ─ Dashboard loads with data from 13:00-14:00
Time: 14:00:30 ─ Dashboard refreshes, shows 13:00:30-14:00:30
Time: 14:01:00 ─ Dashboard refreshes, shows 13:01:00-14:01:00
...
```

### Time Range: Last 1 hour (default)

**Customization Options**:
- Last 1 hour (default)
- Last 6 hours
- Last 24 hours
- Last 7 days
- Custom range

---

## Interactive Features

### Panel Interactions

1. **Click on pie chart slice**: Drill down to specific model/role
2. **Hover on timeseries line**: Show value at that time
3. **Click legend item**: Toggle series visibility
4. **Zoom on timeseries**: Click and drag to zoom to time range
5. **Reset zoom**: Double-click to reset

### Dashboard Controls

1. **Time range selector** (top right): Change time window
2. **Refresh button**: Manually refresh data
3. **Dashboard settings**: Adjust refresh rate, time range
4. **Export**: Export metrics as CSV/JSON
5. **Share**: Share dashboard with team

---

## Expected Data Patterns

### Normal Operation
```
Token Throughput: Steady lines, consistent consumption
Cache Hit Rate: Green (40%+), indicating good caching
Daily Cost: Yellow or green, within budget
Cost Trend: Flat or slightly declining
```

### High Activity
```
Token Throughput: Spikes in all three lines
Task Throughput: Increased tasks/min
Queue Depth: Increased pending tasks
Cost: Higher daily cost
```

### Performance Issue
```
Error Rate: Spike above 1%
Success Rate: Drop below 95%
Validation Errors: Spike in error rate
Queue Depth: Increased backlog
```

### Cost Optimization Needed
```
Daily Cost: Red (>$500)
Cost Trend: Upward trend
Cost by Model: Opus >40%
Cache Hit Rate: Red (<20%)
```

---

## Screenshots Checklist

When dashboard is deployed, capture screenshots of:

- [ ] Full dashboard overview (all panels visible)
- [ ] Panel 12: Token Throughput (normal operation)
- [ ] Panel 13: Token by Model (pie chart)
- [ ] Panel 14: Tokens per Task (histogram)
- [ ] Panel 15: Cache Hit Rate (gauge - green)
- [ ] Panel 16: Daily Cost (stat card)
- [ ] Panel 17: Cost by Role (pie chart)
- [ ] Panel 18: Cost by Model (pie chart)
- [ ] Panel 19: Cost per Task (histogram)
- [ ] Panel 20: Cost Trend (7-day area chart)
- [ ] Dashboard with high activity (spikes)
- [ ] Dashboard with cost optimization needed (red thresholds)
- [ ] Dashboard with custom time range selected
- [ ] Dashboard export dialog

---

## Accessibility Notes

### Color Blindness Considerations
- Use distinct line styles (solid, dashed, dotted)
- Include legends with text labels
- Avoid red/green only for status (use icons too)

### Mobile Viewing
- Dashboard may need horizontal scrolling
- Consider responsive layout for mobile
- Test on tablet and phone sizes

### Performance
- Dashboard should load within 2 seconds
- Refresh should complete within 5 seconds
- No blocking operations

---

**Visual Documentation Complete** ✅

All panel visualizations documented with expected appearance, color coding, and interpretation guides.
