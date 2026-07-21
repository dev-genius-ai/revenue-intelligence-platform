with source as (

    select * from {{ source('raw', 'user_signups') }}

),

cleaned as (

    select
        upper(nullif(trim(user_id), '')) as user_id,
        try_cast(nullif(trim(signup_date), '') as date) as signup_date,
        cast(
            date_trunc(
                'month',
                try_cast(nullif(trim(signup_date), '') as date)
            ) as date
        ) as signup_month,
        upper(nullif(trim(company_id), '')) as company_id,
        lower(nullif(trim(referral_source), '')) as referral_source,
        case
            when lower(nullif(trim(utm_source), '')) in ('x', 'twitter/x')
                then 'twitter'
            else lower(nullif(trim(utm_source), ''))
        end as utm_source,
        lower(nullif(trim(utm_medium), '')) as utm_medium,
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
        ) as utm_campaign,
        case
            when lower(nullif(trim(first_touch_channel), '')) in ('x', 'twitter/x')
                then 'twitter'
            else lower(nullif(trim(first_touch_channel), ''))
        end as first_touch_channel,
        case
            when lower(nullif(trim(last_touch_channel), '')) in ('x', 'twitter/x')
                then 'twitter'
            else lower(nullif(trim(last_touch_channel), ''))
        end as last_touch_channel
    from source

)

select * from cleaned
