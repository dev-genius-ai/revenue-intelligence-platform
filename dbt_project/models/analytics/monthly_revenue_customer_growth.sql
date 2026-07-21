with revenue as (

    select * from {{ ref('fct_attributed_revenue') }}

),

dates as (

    select * from {{ ref('dim_time') }}

),

monthly_metrics as (

    select
        dates.month_key,
        dates.month_start_date,
        min(revenue.revenue_date_key) as month_date_key,
        sum(revenue.revenue_amount) as total_revenue,
        sum(
            case when revenue.is_recurring then revenue.revenue_amount else 0 end
        ) as recurring_revenue,
        sum(
            case when not revenue.is_recurring then revenue.revenue_amount else 0 end
        ) as initial_revenue,
        count(*) as revenue_record_count,
        count(distinct revenue.user_id) as active_customers,
        count(
            distinct case
                when revenue.cohort_key = dates.month_key then revenue.user_id
            end
        ) as new_customers
    from revenue
    inner join dates
        on revenue.revenue_date_key = dates.date_key
    group by
        dates.month_key,
        dates.month_start_date

),

with_prior_month as (

    select
        *,
        lag(total_revenue) over (order by month_key) as prior_month_revenue,
        lag(active_customers) over (order by month_key)
            as prior_month_active_customers
    from monthly_metrics

)

select
    month_key,
    month_date_key,
    month_start_date,
    total_revenue,
    recurring_revenue,
    initial_revenue,
    revenue_record_count,
    active_customers,
    new_customers,
    total_revenue - prior_month_revenue as revenue_change,
    round(
        (total_revenue - prior_month_revenue)
        / nullif(prior_month_revenue, 0),
        6
    ) as revenue_growth_rate,
    active_customers - prior_month_active_customers as customer_change,
    round(
        (active_customers - prior_month_active_customers)::double
        / nullif(prior_month_active_customers, 0),
        6
    ) as customer_growth_rate
from with_prior_month
