with companies as (

    select * from {{ ref('dim_company') }}

),

revenue as (

    select * from {{ ref('fct_attributed_revenue') }}

),

company_metrics as (

    select
        company_id,
        sum(revenue_amount) as total_revenue,
        sum(
            case when is_recurring then revenue_amount else 0 end
        ) as recurring_revenue,
        sum(
            case when not is_recurring then revenue_amount else 0 end
        ) as initial_revenue,
        count(*) as revenue_record_count,
        count(distinct user_id) as customer_count,
        count(distinct first_touch_channel) as first_touch_channel_count,
        count(distinct last_touch_channel) as last_touch_channel_count,
        sum(
            case
                when first_touch_campaign_id is not null then revenue_amount
                else 0
            end
        ) as first_touch_campaign_revenue,
        sum(
            case
                when last_touch_campaign_id is not null then revenue_amount
                else 0
            end
        ) as last_touch_campaign_revenue
    from revenue
    group by company_id

)

select
    companies.company_id,
    companies.company_name,
    companies.industry,
    coalesce(company_metrics.total_revenue, 0) as total_revenue,
    coalesce(company_metrics.recurring_revenue, 0) as recurring_revenue,
    coalesce(company_metrics.initial_revenue, 0) as initial_revenue,
    coalesce(company_metrics.revenue_record_count, 0)
        as revenue_record_count,
    coalesce(company_metrics.customer_count, 0) as customer_count,
    coalesce(company_metrics.first_touch_channel_count, 0)
        as first_touch_channel_count,
    coalesce(company_metrics.last_touch_channel_count, 0)
        as last_touch_channel_count,
    coalesce(company_metrics.first_touch_campaign_revenue, 0)
        as first_touch_campaign_revenue,
    coalesce(company_metrics.last_touch_campaign_revenue, 0)
        as last_touch_campaign_revenue,
    round(
        coalesce(company_metrics.total_revenue, 0)
        / nullif(coalesce(company_metrics.customer_count, 0), 0),
        2
    ) as average_revenue_per_customer,
    round(
        coalesce(company_metrics.total_revenue, 0)
        / nullif(sum(company_metrics.total_revenue) over (), 0),
        6
    ) as portfolio_revenue_share
from companies
left join company_metrics
    using (company_id)
