with mart_revenue as (

    select sum(revenue_amount) as total_revenue
    from {{ ref('fct_attributed_revenue') }}

),

mart_campaigns as (

    select
        sum(budget_usd) as campaign_budget,
        sum(first_touch_attributed_revenue) as first_touch_campaign_revenue,
        sum(last_touch_attributed_revenue) as last_touch_campaign_revenue
    from {{ ref('fct_campaign_roi') }}

),

validations as (

    select
        'channel_first_touch_revenue' as check_name,
        mart_revenue.total_revenue as expected_value,
        sum(channel_performance.first_touch_revenue) as actual_value
    from {{ ref('channel_performance') }}
    cross join mart_revenue
    group by mart_revenue.total_revenue

    union all

    select
        'channel_last_touch_revenue',
        mart_revenue.total_revenue,
        sum(channel_performance.last_touch_revenue)
    from {{ ref('channel_performance') }}
    cross join mart_revenue
    group by mart_revenue.total_revenue

    union all

    select
        'company_total_revenue',
        mart_revenue.total_revenue,
        sum(company_revenue_analysis.total_revenue)
    from {{ ref('company_revenue_analysis') }}
    cross join mart_revenue
    group by mart_revenue.total_revenue

    union all

    select
        'monthly_total_revenue',
        mart_revenue.total_revenue,
        sum(monthly_revenue_customer_growth.total_revenue)
    from {{ ref('monthly_revenue_customer_growth') }}
    cross join mart_revenue
    group by mart_revenue.total_revenue

    union all

    select
        'campaign_budget',
        mart_campaigns.campaign_budget,
        sum(campaign_performance.budget_usd)
    from {{ ref('campaign_performance') }}
    cross join mart_campaigns
    group by mart_campaigns.campaign_budget

    union all

    select
        'campaign_first_touch_revenue',
        mart_campaigns.first_touch_campaign_revenue,
        sum(campaign_performance.first_touch_attributed_revenue)
    from {{ ref('campaign_performance') }}
    cross join mart_campaigns
    group by mart_campaigns.first_touch_campaign_revenue

    union all

    select
        'campaign_last_touch_revenue',
        mart_campaigns.last_touch_campaign_revenue,
        sum(campaign_performance.last_touch_attributed_revenue)
    from {{ ref('campaign_performance') }}
    cross join mart_campaigns
    group by mart_campaigns.last_touch_campaign_revenue

)

select *
from validations
where abs(expected_value - actual_value) > 0.01
