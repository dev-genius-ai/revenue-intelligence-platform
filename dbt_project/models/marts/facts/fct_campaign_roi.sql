with campaigns as (

    select * from {{ ref('stg_campaign_metadata') }}

),

attributed_revenue as (

    select * from {{ ref('int_attributed_revenue') }}

),

first_touch_metrics as (

    select
        first_touch_campaign as campaign_id,
        sum(revenue_amount) as first_touch_attributed_revenue,
        count(distinct user_id) as first_touch_customers
    from attributed_revenue
    where first_touch_campaign is not null
    group by first_touch_campaign

),

last_touch_metrics as (

    select
        last_touch_campaign as campaign_id,
        sum(revenue_amount) as last_touch_attributed_revenue,
        count(distinct user_id) as last_touch_customers
    from attributed_revenue
    where last_touch_campaign is not null
    group by last_touch_campaign

)

select
    campaigns.campaign_id,
    campaigns.channel,
    campaigns.target_company_id,
    cast(strftime(campaigns.start_date, '%Y%m%d') as integer)
        as start_date_key,
    cast(strftime(campaigns.end_date, '%Y%m%d') as integer)
        as end_date_key,
    campaigns.budget_usd,
    coalesce(first_touch_metrics.first_touch_attributed_revenue, 0)
        as first_touch_attributed_revenue,
    coalesce(last_touch_metrics.last_touch_attributed_revenue, 0)
        as last_touch_attributed_revenue,
    coalesce(first_touch_metrics.first_touch_customers, 0)
        as first_touch_customers,
    coalesce(last_touch_metrics.last_touch_customers, 0)
        as last_touch_customers,
    round(
        coalesce(first_touch_metrics.first_touch_attributed_revenue, 0)
        / nullif(campaigns.budget_usd, 0),
        4
    ) as first_touch_roas,
    round(
        coalesce(last_touch_metrics.last_touch_attributed_revenue, 0)
        / nullif(campaigns.budget_usd, 0),
        4
    ) as last_touch_roas,
    round(
        (
            coalesce(first_touch_metrics.first_touch_attributed_revenue, 0)
            - campaigns.budget_usd
        ) / nullif(campaigns.budget_usd, 0),
        4
    ) as first_touch_roi,
    round(
        (
            coalesce(last_touch_metrics.last_touch_attributed_revenue, 0)
            - campaigns.budget_usd
        ) / nullif(campaigns.budget_usd, 0),
        4
    ) as last_touch_roi
from campaigns
left join first_touch_metrics
    using (campaign_id)
left join last_touch_metrics
    using (campaign_id)
