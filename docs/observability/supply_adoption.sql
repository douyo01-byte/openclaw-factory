SELECT
source,
COUNT(*) AS proposals,
SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
SUM(CASE WHEN status='merged' THEN 1 ELSE 0 END) AS merged,
ROUND(
SUM(CASE WHEN status='merged' THEN 1 ELSE 0 END)*1.0 /
NULLIF(COUNT(*),0)
,3) AS merge_rate
FROM dev_proposals
GROUP BY source
ORDER BY merge_rate DESC;
