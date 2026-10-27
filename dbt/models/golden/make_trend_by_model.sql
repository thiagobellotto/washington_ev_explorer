select model_year, make, model, count(*) as vehicle_count
from {{ ref('enriched_electric_vehicles') }}
where quality_status = 'accepted'
group by model_year, make, model
