with cohorts as (

    select distinct signup_month as cohort_month
    from {{ ref('stg_user_signups') }}
    where signup_month is not null

)

select
    cast(strftime(cohort_month, '%Y%m') as integer) as cohort_key,
    cohort_month,
    strftime(cohort_month, '%Y-%m') as cohort_label,
    extract(month from cohort_month)::integer as cohort_month_number,
    extract(quarter from cohort_month)::integer as cohort_quarter,
    extract(year from cohort_month)::integer as cohort_year
from cohorts
