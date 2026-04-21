{{config_block}}

with base as (

    select * from {{upstream_reference}}

),

final as (

    select
{{mart_select_list}}
    from base
{{where_clause}}
{{group_by_clause}}

)

select * from final
