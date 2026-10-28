-- Optimized report: read the precomputed category summary.

SELECT
    category,
    revenue,
    units_sold,
    completed_orders
FROM category_sales_summary
ORDER BY category;
