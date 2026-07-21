with source_dates as (

    select publish_date as date_day
    from {{ ref('stg_content_performance') }}

    union all

    select signup_date as date_day
    from {{ ref('stg_user_signups') }}

    union all

    select revenue_month as date_day
    from {{ ref('stg_portfolio_revenue') }}

    union all

    select start_date as date_day
    from {{ ref('stg_campaign_metadata') }}

    union all

    select end_date as date_day
    from {{ ref('stg_campaign_metadata') }}

),

date_bounds as (

    select
        min(date_day) as minimum_date,
        max(date_day) as maximum_date
    from source_dates

),

date_spine as (

    select cast(generated_date as date) as date_day
    from date_bounds,
    generate_series(
        minimum_date,
        maximum_date,
        interval 1 day
    ) as generated_dates(generated_date)

)

select
    cast(strftime(date_day, '%Y%m%d') as integer) as date_key,
    date_day,
    cast(date_trunc('week', date_day) as date) as week_start_date,
    cast(date_trunc('month', date_day) as date) as month_start_date,
    cast(strftime(date_day, '%Y%m') as integer) as month_key,
    extract(day from date_day)::integer as day_of_month,
    extract(month from date_day)::integer as month_number,
    strftime(date_day, '%B') as month_name,
    extract(quarter from date_day)::integer as quarter_number,
    extract(year from date_day)::integer as year_number,
    extract(isodow from date_day)::integer as iso_day_of_week,
    extract(isodow from date_day) in (6, 7) as is_weekend
from date_spine
