SELECT
    competence,
    COUNT(*) AS nb,
    region
FROM offres_historique
WHERE competence IS NOT NULL
  AND competence <> ''
  AND region IS NOT NULL
  AND region <> ''
GROUP BY competence, region;
