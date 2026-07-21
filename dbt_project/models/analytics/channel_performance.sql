with channels as (

    select * from {{ ref('dim_channel') }}

),

revenue as (

    select * from {{ ref('fct_attributed_revenue') }}

),

content as (

    select * from {{ ref('fct_content_performance') }}

),

campaigns as (

    select * from {{ ref('fct_campaign_roi') }}

),

first_touch_revenue as (

    select
        first_touch_channel as channel_key,
        sum(revenue_amount) as first_touch_revenue,
        count(distinct user_id) as first_touch_customers,
        count(*) as first_touch_revenue_records
    from revenue
    group by first_touch_channel

),

last_touch_revenue as (

    select
        last_touch_channel as channel_key,
        sum(revenue_amount) as last_touch_revenue,
        count(distinct user_id) as last_touch_customers,
        count(*) as last_touch_revenue_records
    from revenue
    group by last_touch_channel

),

content_metrics as (

    select
        channel as channel_key,
        sum(content_count) as content_count,
        sum(views) as views,
        sum(clicks) as clicks
    from content
    group by channel

),

campaign_metrics as (

    select
        channel as channel_key,
        count(*) as campaign_count,
        sum(budget_usd) as campaign_budget_usd
    from campaigns
    group by channel

)

select
    channels.channel_key,
    channels.channel_name,
    channels.channel_group,
    coalesce(first_touch_revenue.first_touch_revenue, 0)
        as first_touch_revenue,
    coalesce(last_touch_revenue.last_touch_revenue, 0)
        as last_touch_revenue,
    coalesce(first_touch_revenue.first_touch_customers, 0)
        as first_touch_customers,
    coalesce(last_touch_revenue.last_touch_customers, 0)
        as last_touch_customers,
    coalesce(first_touch_revenue.first_touch_revenue_records, 0)
        as first_touch_revenue_records,
    coalesce(last_touch_revenue.last_touch_revenue_records, 0)
        as last_touch_revenue_records,
    coalesce(content_metrics.content_count, 0) as content_count,
    coalesce(content_metrics.views, 0) as views,
    coalesce(content_metrics.clicks, 0) as clicks,
    round(
        coalesce(content_metrics.clicks, 0)::double
        / nullif(coalesce(content_metrics.views, 0), 0),
        6
    ) as click_through_rate,
    coalesce(campaign_metrics.campaign_count, 0) as campaign_count,
    coalesce(campaign_metrics.campaign_budget_usd, 0)
        as campaign_budget_usd
from channels
left join first_touch_revenue
    using (channel_key)
left join last_touch_revenue
    using (channel_key)
left join content_metrics
    using (channel_key)
left join campaign_metrics
    using (channel_key)
