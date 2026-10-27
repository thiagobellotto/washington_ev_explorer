select * from {{ ref('yearly_trend') }} where vehicle_count <= 0
