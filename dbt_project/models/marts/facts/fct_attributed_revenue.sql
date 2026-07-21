with attributed_revenue as (

    select * from {{ ref('int_attributed_revenue') }}

)

select
    revenue_id,
    user_id,
    company_id,
    cast(strftime(revenue_month, '%Y%m%d') as integer) as revenue_date_key,
    cast(strftime(signup_date, '%Y%m%d') as integer) as signup_date_key,
    cast(strftime(signup_date, '%Y%m') as integer) as cohort_key,
    first_touch_resolved_channel as first_touch_channel,
    last_touch_resolved_channel as last_touch_channel,
    first_touch_campaign as first_touch_campaign_id,
    last_touch_campaign as last_touch_campaign_id,
    first_touch_attribution_reason,
    last_touch_attribution_reason,
    revenue_amount,
    is_recurring,
    has_channel_conflict,
    missing_utm_flag,
    first_touch_campaign_match_status,
    last_touch_campaign_match_status,
    campaign_match_status,
    attribution_confidence
from attributed_revenue
