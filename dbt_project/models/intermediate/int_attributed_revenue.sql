with revenue as (

    select * from {{ ref('stg_portfolio_revenue') }}

),

journeys as (

    select * from {{ ref('int_user_journeys') }}

)

select
    revenue.revenue_id,
    revenue.user_id,
    revenue.company_id,
    revenue.revenue_amount,
    revenue.revenue_month,
    revenue.is_recurring,
    journeys.signup_date,
    journeys.first_touch_channel,
    journeys.last_touch_channel,
    journeys.first_touch_resolved_channel,
    journeys.last_touch_resolved_channel,
    journeys.first_touch_attribution_reason,
    journeys.last_touch_attribution_reason,
    journeys.first_touch_campaign_id as first_touch_campaign,
    journeys.last_touch_campaign_id as last_touch_campaign,
    journeys.has_channel_conflict,
    journeys.missing_utm_flag,
    journeys.first_touch_campaign_match_status,
    journeys.last_touch_campaign_match_status,
    journeys.campaign_match_status,
    journeys.attribution_confidence,
    journeys.user_id is null as missing_journey_flag
from revenue
left join journeys
    on revenue.user_id = journeys.user_id
