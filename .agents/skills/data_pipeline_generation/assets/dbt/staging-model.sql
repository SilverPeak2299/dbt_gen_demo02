{{config_block}}

with source as (

    select * from {{source_reference}}

),

renamed as (

    select
{{staging_select_list}}
    from source

)

select * from renamed
