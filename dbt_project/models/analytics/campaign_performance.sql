with campaigns as (

    select * from {{ ref('fct_campaign_roi') }}

),

channels as (

    select * from {{ ref('dim_channel') }}

),

companies as (

    select * from {{ ref('dim_company') }}

),

dates as (

    select * from {{ ref('dim_time') }}

)

select
    campaigns.campaign_id,
    campaigns.channel as channel_key,
    channels.channel_name,
    campaigns.target_company_id,
    companies.company_name as target_company_name,
    start_dates.date_day as start_date,
    end_dates.date_day as end_date,
    campaigns.budget_usd,
    campaigns.first_touch_attributed_revenue,
    campaigns.last_touch_attributed_revenue,
    campaigns.first_touch_customers,
    campaigns.last_touch_customers,
    campaigns.first_touch_roas,
    campaigns.last_touch_roas,
    campaigns.first_touch_roi,
    campaigns.last_touch_roi,
    round(
        campaigns.budget_usd
        / nullif(campaigns.first_touch_customers, 0),
        2
    ) as first_touch_cost_per_customer,
    round(
        campaigns.budget_usd
        / nullif(campaigns.last_touch_customers, 0),
        2
    ) as last_touch_cost_per_customer,
    campaigns.last_touch_attributed_revenue
        - campaigns.first_touch_attributed_revenue
        as attribution_revenue_difference
from campaigns
inner join channels
    on campaigns.channel = channels.channel_key
left join companies
    on campaigns.target_company_id = companies.company_id
inner join dates as start_dates
    on campaigns.start_date_key = start_dates.date_key
inner join dates as end_dates
    on campaigns.end_date_key = end_dates.date_key
