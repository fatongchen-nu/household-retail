# Data Directory

Place the retail source CSV files here before running the workflow:

```text
transaction_data.csv
campaign_table.csv
campaign_desc.csv
coupon.csv
coupon_redempt.csv
hh_demographic.csv
product.csv
```

Raw CSV files are intentionally ignored by git because some source files exceed GitHub's 100MB file limit. The generated evidence packet, memo, Tableau CSV extracts, and workbook are committed separately.
