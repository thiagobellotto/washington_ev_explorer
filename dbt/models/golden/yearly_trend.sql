-- Model-year composition of the current snapshot, not annual adoption.
select model_year, count(*) as vehicle_count
from {{ ref('enriched_electric_vehicles') }}
where quality_status = 'accepted'
group by model_year
