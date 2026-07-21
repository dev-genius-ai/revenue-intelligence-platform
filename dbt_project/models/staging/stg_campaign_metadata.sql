with source as (

    select * from {{ source('raw', 'campaign_metadata') }}

),

cleaned as (

    select
        upper(nullif(trim(campaign_id), '')) as campaign_id,
        nullif(trim(campaign_name), '') as campaign_name,
        nullif(
            trim(
                both '_' from regexp_replace(
                    lower(trim(campaign_name)),
                    '[^a-z0-9]+',
                    '_',
                    'g'
                )
            ),
            ''
        ) as campaign_slug,
        case
            when lower(nullif(trim(channel), '')) in ('x', 'twitter/x')
                then 'twitter'
            else lower(nullif(trim(channel), ''))
        end as channel,
        cast(budget_usd as decimal(18, 2)) as budget_usd,
        try_cast(nullif(trim(start_date), '') as date) as start_date,
        try_cast(nullif(trim(end_date), '') as date) as end_date,
        upper(nullif(trim(target_company_id), '')) as target_company_id
    from source

)

select * from cleaned
