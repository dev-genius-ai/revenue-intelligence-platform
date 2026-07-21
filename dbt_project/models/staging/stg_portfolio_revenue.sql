with source as (

    select * from {{ source('raw', 'portfolio_revenue') }}

),

cleaned as (

    select
        upper(nullif(trim(revenue_id), '')) as revenue_id,
        upper(nullif(trim(company_id), '')) as company_id,
        upper(nullif(trim(user_id), '')) as user_id,
        cast(
            try_strptime(nullif(trim(month), ''), '%Y-%m') as date
        ) as revenue_month,
        cast(revenue_amount as decimal(18, 2)) as revenue_amount,
        cast(is_recurring as boolean) as is_recurring
    from source

)

select * from cleaned
