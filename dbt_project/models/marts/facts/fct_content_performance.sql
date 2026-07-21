with content as (

    select * from {{ ref('stg_content_performance') }}

),

campaigns as (

    select * from {{ ref('stg_campaign_metadata') }}

),

content_with_campaign as (

    select
        content.content_id,
        content.publish_month,
        content.channel,
        campaigns.campaign_id,
        content.views,
        content.clicks
    from content
    left join campaigns
        on content.utm_campaign = campaigns.campaign_slug
        and content.publish_date between campaigns.start_date and campaigns.end_date
        and content.channel = campaigns.channel

),

aggregated as (

    select
        publish_month,
        channel,
        campaign_id,
        count(*) as content_count,
        sum(views)::bigint as views,
        sum(clicks)::bigint as clicks
    from content_with_campaign
    group by
        publish_month,
        channel,
        campaign_id

)

select
    md5(
        concat(
            cast(publish_month as varchar),
            '|',
            channel,
            '|',
            coalesce(campaign_id, 'NO_CAMPAIGN')
        )
    ) as content_performance_key,
    cast(strftime(publish_month, '%Y%m%d') as integer)
        as publish_month_date_key,
    channel,
    campaign_id,
    content_count,
    views,
    clicks,
    round(clicks::double / nullif(views, 0), 6) as click_through_rate
from aggregated
