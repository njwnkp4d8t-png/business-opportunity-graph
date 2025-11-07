-- ESRI enrichment: update block_groups metrics from ESRI tables
-- Assumes you have imported ESRI tables similar to:
--   esri_business_data(std_geography_id, "N01_BUS", "S23_EMP", "N37_SALES", ...)
--   esri_consumer_spending_data_(std_geography_id, "DI100_CY", "DI150_CY", ...)
-- Mapping rule (as used in original repo):
--   TRIM(LEADING '0' FROM SUBSTR(std_geography_id::text, 5)) = block_groups.ctblockgroup::text

-- Business metrics (stores, employees, sales)
-- Adjust column names if your import uses lowercase
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_name = 'esri_business_data'
  ) THEN
    RAISE NOTICE 'Updating block_groups from esri_business_data...';
    UPDATE block_groups bg
    SET
      n01_bus = bd."N01_BUS",
      s23_emp = bd."S23_EMP",
      n37_sales = bd."N37_SALES"
    FROM esri_business_data bd
    WHERE TRIM(LEADING '0' FROM SUBSTR(bd.std_geography_id::text, 5)) = bg.ctblockgroup::text;
  ELSE
    RAISE NOTICE 'esri_business_data not found; skipping business enrichment';
  END IF;
END $$;

-- Consumer spending / income distribution (example)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_name = 'esri_consumer_spending_data_'
  ) THEN
    RAISE NOTICE 'Updating block_groups from esri_consumer_spending_data_...';
    UPDATE block_groups bg
    SET
      di100_cy = cs."DI100_CY",
      di150_cy = cs."DI150_CY"
    FROM esri_consumer_spending_data_ cs
    WHERE TRIM(LEADING '0' FROM SUBSTR(cs.std_geography_id::text, 5)) = bg.ctblockgroup::text;
  ELSE
    RAISE NOTICE 'esri_consumer_spending_data_ not found; skipping consumer enrichment';
  END IF;
END $$;

