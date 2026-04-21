{{config_block}}

with {{upstream_ctes}} as (

    select * from {{upstream_reference}}

),

transformed as (

    select
{{intermediate_select_list}}
    from {{primary_cte_name}}
{{join_clauses}}
{{where_clause}}

)

select * from transformed
