select
    'channel_performance' as model_name,
    count(*) as invalid_row_count
from {{ ref('channel_performance') }}
where first_touch_revenue < 0
    or last_touch_revenue < 0
    or first_touch_customers < 0
    or last_touch_customers < 0
    or first_touch_revenue_records < 0
    or last_touch_revenue_records < 0
    or content_count < 0
    or views < 0
    or clicks < 0
    or click_through_rate < 0
    or campaign_count < 0
    or campaign_budget_usd < 0
having count(*) > 0

union all

select
    'campaign_performance',
    count(*)
from {{ ref('campaign_performance') }}
where budget_usd < 0
    or first_touch_attributed_revenue < 0
    or last_touch_attributed_revenue < 0
    or first_touch_customers < 0
    or last_touch_customers < 0
    or first_touch_roas < 0
    or last_touch_roas < 0
    or first_touch_cost_per_customer < 0
    or last_touch_cost_per_customer < 0
having count(*) > 0

union all

select
    'company_revenue_analysis',
    count(*)
from {{ ref('company_revenue_analysis') }}
where total_revenue < 0
    or recurring_revenue < 0
    or initial_revenue < 0
    or revenue_record_count < 0
    or customer_count < 0
    or first_touch_channel_count < 0
    or last_touch_channel_count < 0
    or first_touch_campaign_revenue < 0
    or last_touch_campaign_revenue < 0
    or average_revenue_per_customer < 0
    or portfolio_revenue_share < 0
having count(*) > 0

union all

select
    'monthly_revenue_customer_growth',
    count(*)
from {{ ref('monthly_revenue_customer_growth') }}
where total_revenue < 0
    or recurring_revenue < 0
    or initial_revenue < 0
    or revenue_record_count < 0
    or active_customers < 0
    or new_customers < 0
having count(*) > 0
