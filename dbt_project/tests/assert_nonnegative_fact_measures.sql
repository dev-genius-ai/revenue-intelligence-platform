select
    'fct_attributed_revenue.revenue_amount' as measure_name,
    count(*) as invalid_row_count
from {{ ref('fct_attributed_revenue') }}
where revenue_amount < 0
having count(*) > 0

union all

select
    'fct_campaign_roi.measures' as measure_name,
    count(*) as invalid_row_count
from {{ ref('fct_campaign_roi') }}
where budget_usd < 0
    or first_touch_attributed_revenue < 0
    or last_touch_attributed_revenue < 0
    or first_touch_customers < 0
    or last_touch_customers < 0
    or first_touch_roas < 0
    or last_touch_roas < 0
having count(*) > 0

union all

select
    'fct_content_performance.measures' as measure_name,
    count(*) as invalid_row_count
from {{ ref('fct_content_performance') }}
where content_count < 0
    or views < 0
    or clicks < 0
    or click_through_rate < 0
having count(*) > 0
