with signups as (

    select * from {{ ref('stg_user_signups') }}

),

campaigns as (

    select * from {{ ref('stg_campaign_metadata') }}

),

resolved_channels as (

    select
        user_id,
        company_id,
        signup_date,
        first_touch_channel,
        last_touch_channel,
        utm_source,
        utm_medium,
        utm_campaign,
        referral_source,
        coalesce(
            first_touch_channel,
            utm_source,
            referral_source,
            'unknown'
        ) as first_touch_resolved_channel,
        case
            when first_touch_channel is not null then 'first_touch_channel'
            when utm_source is not null then 'utm_source'
            when referral_source is not null then 'referral_source'
            else 'unknown'
        end as first_touch_attribution_reason,
        coalesce(
            last_touch_channel,
            utm_source,
            referral_source,
            'unknown'
        ) as last_touch_resolved_channel,
        case
            when last_touch_channel is not null then 'last_touch_channel'
            when utm_source is not null then 'utm_source'
            when referral_source is not null then 'referral_source'
            else 'unknown'
        end as last_touch_attribution_reason,
        coalesce(first_touch_channel <> last_touch_channel, false)
            as has_channel_conflict,
        (
            utm_source is null
            or utm_medium is null
            or utm_campaign is null
        ) as missing_utm_flag
    from signups

),

campaign_matches as (

    select
        journeys.*,
        first_campaign.campaign_id as first_touch_campaign_id,
        last_campaign.campaign_id as last_touch_campaign_id
    from resolved_channels as journeys
    left join campaigns as first_campaign
        on journeys.utm_campaign = first_campaign.campaign_slug
        and journeys.signup_date between
            first_campaign.start_date and first_campaign.end_date
        and (
            first_campaign.target_company_id is null
            or journeys.company_id = first_campaign.target_company_id
        )
        and journeys.first_touch_resolved_channel = first_campaign.channel
    left join campaigns as last_campaign
        on journeys.utm_campaign = last_campaign.campaign_slug
        and journeys.signup_date between
            last_campaign.start_date and last_campaign.end_date
        and (
            last_campaign.target_company_id is null
            or journeys.company_id = last_campaign.target_company_id
        )
        and journeys.last_touch_resolved_channel = last_campaign.channel

),

quality_flags as (

    select
        *,
        case
            when utm_campaign is null then 'missing_utm_campaign'
            when first_touch_campaign_id is not null then 'matched'
            else 'unmatched_or_invalid'
        end as first_touch_campaign_match_status,
        case
            when utm_campaign is null then 'missing_utm_campaign'
            when last_touch_campaign_id is not null then 'matched'
            else 'unmatched_or_invalid'
        end as last_touch_campaign_match_status,
        case
            when utm_campaign is null then 'missing_utm_campaign'
            when first_touch_campaign_id is not null
                and last_touch_campaign_id is not null
                then 'matched_both'
            when first_touch_campaign_id is not null
                then 'matched_first_touch_only'
            when last_touch_campaign_id is not null
                then 'matched_last_touch_only'
            else 'unmatched_or_invalid'
        end as campaign_match_status,
        case
            when first_touch_resolved_channel = 'unknown'
                or last_touch_resolved_channel = 'unknown'
                then 'low'
            when first_touch_campaign_id is not null
                and last_touch_campaign_id is not null
                and not has_channel_conflict
                and not missing_utm_flag
                then 'high'
            when first_touch_attribution_reason = 'referral_source'
                or last_touch_attribution_reason = 'referral_source'
                then 'low'
            else 'medium'
        end as attribution_confidence
    from campaign_matches

)

select * from quality_flags
