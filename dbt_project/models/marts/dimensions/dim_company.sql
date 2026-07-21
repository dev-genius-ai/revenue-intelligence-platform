with observed_companies as (

    select company_id
    from {{ ref('stg_user_signups') }}

    union

    select company_id
    from {{ ref('stg_portfolio_revenue') }}

    union

    select target_company_id as company_id
    from {{ ref('stg_campaign_metadata') }}
    where target_company_id is not null

),

described as (

    select
        company_id,
        case company_id
            when 'CTC-001' then 'GreenLeaf Landscaping'
            when 'CTC-002' then 'BrightPath Education'
            when 'CTC-003' then 'QuickFix Auto Repair'
            when 'CTC-004' then 'Summit Dental Group'
        end as company_name,
        case company_id
            when 'CTC-001' then 'Home Services'
            when 'CTC-002' then 'Education'
            when 'CTC-003' then 'Automotive'
            when 'CTC-004' then 'Healthcare'
        end as industry
    from observed_companies

)

select * from described
