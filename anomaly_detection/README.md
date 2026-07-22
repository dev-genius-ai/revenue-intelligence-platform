# Anomaly Detection

Detect months where a channel's last-touch attributed revenue deviates from its
recent historical trend using a simple rolling statistical baseline.

## Method

For each channel and calendar month:

1. Aggregate monthly last-touch revenue from `marts.fct_attributed_revenue`.
2. Exclude the `unknown` channel.
3. Compute a **6-month rolling mean** and **rolling standard deviation** on the
   **prior** six months (current month excluded). A full six months of history is
   required before a row is scored; warm-up months are omitted from the output.
4. Score the current month:

```text
z_score = (current_revenue - rolling_mean) / rolling_std
expected_revenue = rolling_mean
revenue_difference = current_revenue - expected_revenue
deviation_percent = revenue_difference / expected_revenue * 100
```

5. Flag an anomaly when `ABS(z_score) >= 2.75`.

If `rolling_std = 0`, `z_score` is `NULL` and the row is marked `normal`.
If `rolling_mean = 0`, `deviation_percent` is `NULL`.

## Severity and direction

| Absolute z-score | Severity |
|------------------|----------|
| `< 2.75` or `NULL` | normal  |
| `2.75`–`3.5`       | moderate |
| `> 3.5`            | severe   |

| Condition | `anomaly_direction` |
|-----------|---------------------|
| Not an anomaly | `normal` |
| Anomaly with `z_score > 0` | `positive` |
| Anomaly with `z_score < 0` | `negative` |

`anomaly_rank` ranks flagged anomalies by absolute z-score (1 = largest).
`explanation` is a plain-English summary of the month.

## Data Sources

Read-only inputs (no dbt model changes):

- `analytics.channel_performance` — channel inventory
- `analytics.monthly_revenue_customer_growth` — month spine
- `marts.fct_attributed_revenue` + `marts.dim_time` — monthly channel revenue

## Output

Schema/table: `anomaly.channel_revenue_anomalies`

| Column | Description |
|--------|-------------|
| `month_start_date` | Month start date |
| `channel` | Channel key (`last_touch_channel`) |
| `monthly_revenue` | Aggregated last-touch revenue |
| `expected_revenue` | Rolling 6-month mean |
| `revenue_difference` | Actual minus expected |
| `rolling_mean` | Same as expected revenue |
| `rolling_std` | Std of prior 6 months |
| `z_score` | Standardized deviation (nullable) |
| `deviation_percent` | Percent deviation from expected |
| `is_anomaly` | `true` when `ABS(z_score) >= 2.75` |
| `severity` | `normal` / `moderate` / `severe` |
| `anomaly_direction` | `positive` / `negative` / `normal` |
| `anomaly_rank` | Rank among anomalies by `ABS(z_score)` |
| `explanation` | Plain-English summary |

## Run

```bash
python anomaly_detection/run_anomaly_detection.py
# or
make anomaly
```

## Dashboard

The Streamlit **Anomaly Detection** page defaults to anomaly rows only (toggle to
show all scored months), sorts by descending `|z|`, and color-codes severity.

## Limitations

- Last-touch attribution only; first-touch series are not scored.
- Zero-filled months can create artificial jumps when a channel starts late.
- Not a machine-learning detector (no Isolation Forest, Prophet, etc.).
