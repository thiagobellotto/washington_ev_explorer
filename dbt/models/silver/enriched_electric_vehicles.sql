-- Keep imperfect rows visible so published totals can be reconciled to the source.
with typed as (
    select
        nullif(trim(county), '') as county,
        city,
        state,
        try_cast(model_year as integer) as model_year,
        nullif(trim(make), '') as make,
        model,
        try_cast(electric_range as integer) as electric_range,
        try_cast(split_part(replace(replace(vehicle_location, 'POINT (', ''), ')', ''), ' ', 1) as double) as longitude,
        try_cast(split_part(replace(replace(vehicle_location, 'POINT (', ''), ')', ''), ' ', 2) as double) as latitude
    from {{ ref('raw_electric_vehicles') }}
)
select *,
    case
        when model_year is null or model_year < 1900 or model_year > year(current_date) + 1
            then 'invalid_model_year'
        when make is null then 'missing_make'
        else 'accepted'
    end as quality_status,
    case
        when electric_range is null or electric_range <= 0 then 'Unknown / not reported'
        when electric_range <= 50 then 'Up to 50 miles'
        when electric_range <= 150 then '51–150 miles'
        else 'Over 150 miles'
    end as range_category
from typed
