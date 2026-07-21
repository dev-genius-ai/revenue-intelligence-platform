with observed_channels as (

    select channel as channel_key
    from {{ ref('stg_campaign_metadata') }}

    union

    select channel as channel_key
    from {{ ref('stg_content_performance') }}

    union

    select first_touch_resolved_channel as channel_key
    from {{ ref('int_user_journeys') }}

    union

    select last_touch_resolved_channel as channel_key
    from {{ ref('int_user_journeys') }}

    union

    select 'unknown' as channel_key

),

described as (

    select
        channel_key,
        case channel_key
            when 'youtube' then 'YouTube'
            when 'twitter' then 'Twitter/X'
            when 'instagram' then 'Instagram'
            when 'newsletter' then 'Newsletter'
            when 'podcast' then 'Podcast'
            when 'blog' then 'Blog'
            when 'organic' then 'Organic'
            when 'referral' then 'Referral'
            when 'direct' then 'Direct'
            when 'word_of_mouth' then 'Word of Mouth'
            when 'unknown' then 'Unknown'
            else replace(channel_key, '_', ' ')
        end as channel_name,
        case
            when channel_key in ('youtube', 'twitter', 'instagram')
                then 'social'
            when channel_key in ('newsletter', 'podcast', 'blog')
                then 'owned_content'
            when channel_key = 'organic' then 'organic'
            when channel_key in ('referral', 'direct', 'word_of_mouth')
                then 'referral'
            when channel_key = 'unknown' then 'unknown'
            else 'other'
        end as channel_group
    from observed_channels
    where channel_key is not null

)

select * from described
