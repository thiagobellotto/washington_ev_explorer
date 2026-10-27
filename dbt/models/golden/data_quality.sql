select quality_status, count(*) as row_count
from {{ ref('enriched_electric_vehicles') }}
group by quality_status
