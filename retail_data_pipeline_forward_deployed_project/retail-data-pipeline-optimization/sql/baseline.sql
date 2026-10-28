-- Baseline: join source tables and aggregate for every report request.

SELECT
    p.category,
    SUM(oi.quantity * oi.unit_price) AS revenue,
    SUM(oi.quantity) AS units_sold,
    COUNT(DISTINCT o.order_id) AS completed_orders
FROM clean_order_items AS oi
JOIN clean_orders AS o
    ON oi.order_id = o.order_id
JOIN clean_products AS p
    ON oi.product_id = p.product_id
WHERE o.status = 'COMPLETED'
GROUP BY p.category
ORDER BY p.category;
