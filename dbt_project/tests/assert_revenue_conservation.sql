with intermediate_totals as (

    select
        count(*) as revenue_record_count,
        sum(revenue_amount) as total_revenue
    from {{ ref('int_attributed_revenue') }}

),

fact_totals as (

    select
        count(*) as revenue_record_count,
        sum(revenue_amount) as total_revenue
    from {{ ref('fct_attributed_revenue') }}

)

select
    intermediate_totals.revenue_record_count as intermediate_record_count,
    fact_totals.revenue_record_count as fact_record_count,
    intermediate_totals.total_revenue as intermediate_revenue,
    fact_totals.total_revenue as fact_revenue
from intermediate_totals
cross join fact_totals
where intermediate_totals.revenue_record_count
        <> fact_totals.revenue_record_count
    or abs(
        intermediate_totals.total_revenue - fact_totals.total_revenue
    ) > 0.01
