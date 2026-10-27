with totals as (
    select
        (select count(*) from {{ ref('raw_electric_vehicles') }}) as source_rows,
        (select sum(row_count) from {{ ref('data_quality') }}) as classified_rows,
        (select count(*) from {{ ref('enriched_electric_vehicles') }} where quality_status = 'accepted') as accepted_rows,
        (select coalesce(sum(vehicle_count), 0) from {{ ref('yearly_trend') }}) as year_rows,
        (select coalesce(sum(vehicle_count), 0) from {{ ref('make_trend_by_model') }}) as make_rows,
        (select coalesce(sum(vehicle_count), 0) from {{ ref('county_summary') }}) as county_rows
)
select * from totals
where source_rows = 0 or source_rows <> classified_rows
   or accepted_rows <> year_rows or accepted_rows <> make_rows or accepted_rows <> county_rows
