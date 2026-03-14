# AZTECA: Quick Photo Audit on Staging

**Priority:** Run before promoting staging to production
**From:** Pelé
**Date:** March 13, 2026

We had photo mismatching issues in production. Before we promote, we need to know the state of photo_url in staging.

Run these queries and paste full output:

```sql
-- 1: Overall photo coverage
SELECT
    COUNT(*) AS total_profiles,
    COUNT(*) FILTER (WHERE photo_url IS NOT NULL) AS has_photo,
    COUNT(*) FILTER (WHERE photo_url IS NULL) AS no_photo,
    ROUND(COUNT(*) FILTER (WHERE photo_url IS NOT NULL)::numeric / COUNT(*) * 100, 1) AS photo_pct
FROM profile_players_staging;

-- 2: Photo coverage by confidence level
SELECT
    data_confidence,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE photo_url IS NOT NULL) AS has_photo,
    COUNT(*) FILTER (WHERE photo_url IS NULL) AS no_photo,
    ROUND(COUNT(*) FILTER (WHERE photo_url IS NOT NULL)::numeric / COUNT(*) * 100, 1) AS photo_pct
FROM profile_players_staging
GROUP BY data_confidence
ORDER BY
    CASE data_confidence
        WHEN 'VERIFIED' THEN 1
        WHEN 'PROJECTED' THEN 2
        WHEN 'PARTIAL' THEN 3
        WHEN 'ORPHAN' THEN 4
    END;

-- 3: Photo source breakdown (TM vs APIF by URL pattern)
SELECT
    CASE
        WHEN photo_url LIKE '%transfermarkt%' THEN 'TM'
        WHEN photo_url LIKE '%api-sports%' THEN 'APIF'
        WHEN photo_url LIKE '%default%' THEN 'TM_DEFAULT'
        ELSE 'OTHER'
    END AS photo_source,
    COUNT(*) AS count
FROM profile_players_staging
WHERE photo_url IS NOT NULL
GROUP BY 1
ORDER BY count DESC;

-- 4: TM "default" placeholder photos (these are NOT real photos)
SELECT COUNT(*) AS tm_default_placeholder_photos
FROM profile_players_staging
WHERE photo_url LIKE '%/default.jpg%';

-- 5: Photo coverage for VERIFIED profiles specifically
-- These are the most important — dual-source confirmed players
SELECT
    CASE
        WHEN photo_url LIKE '%transfermarkt%' THEN 'TM photo'
        WHEN photo_url LIKE '%api-sports%' THEN 'APIF photo'
        WHEN photo_url LIKE '%default%' THEN 'TM placeholder'
        WHEN photo_url IS NULL THEN 'NO PHOTO'
        ELSE 'OTHER'
    END AS photo_status,
    COUNT(*) AS count
FROM profile_players_staging
WHERE data_confidence = 'VERIFIED'
GROUP BY 1
ORDER BY count DESC;

-- 6: Sample profiles with NO photo (what are we missing?)
SELECT profile_id, tm_id, apif_id, display_name, data_confidence, match_tier
FROM profile_players_staging
WHERE photo_url IS NULL
ORDER BY data_confidence, display_name
LIMIT 25;

-- 7: Sample VERIFIED profiles where TM had a default placeholder
-- and APIF photo was used as fallback
SELECT profile_id, tm_id, apif_id, display_name, photo_url
FROM profile_players_staging
WHERE data_confidence = 'VERIFIED'
  AND photo_url LIKE '%api-sports%'
LIMIT 15;
```

Save output to **`AZTECA_PHOTO_AUDIT_RESULTS.md`**.
