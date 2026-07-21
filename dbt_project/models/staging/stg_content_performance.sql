with source as (

    select * from {{ source('raw', 'content_performance') }}

),

cleaned as (

    select
        upper(nullif(trim(content_id), '')) as content_id,
        case
            when lower(nullif(trim(channel), '')) in ('x', 'twitter/x')
                then 'twitter'
            else lower(nullif(trim(channel), ''))
        end as channel,
        try_cast(nullif(trim(publish_date), '') as date) as publish_date,
        cast(
            date_trunc(
                'month',
                try_cast(nullif(trim(publish_date), '') as date)
            ) as date
        ) as publish_month,
        cast(views as bigint) as views,
        cast(clicks as bigint) as clicks,
        case
            when lower(nullif(trim(utm_source), '')) in ('x', 'twitter/x')
                then 'twitter'
            else lower(nullif(trim(utm_source), ''))
        end as utm_source,
        nullif(
            trim(
                both '_' from regexp_replace(
                    lower(trim(utm_campaign)),
                    '[^a-z0-9]+',
                    '_',
                    'g'
                )
            ),
            ''
        ) as utm_campaign
    from source

)

select * from cleaned
