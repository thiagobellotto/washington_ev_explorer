select coalesce(county, 'Unknown') as county, count(*) as vehicle_count
from {{ ref('enriched_electric_vehicles') }}
where quality_status = 'accepted'
group by 1
