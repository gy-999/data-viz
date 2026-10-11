# Second fetch round: candidates for business / chinese / excel / dirty-data demos.
$ErrorActionPreference = 'Continue'
$root = "D:\Claude cade\data\_datasets"
$raw  = Join-Path $root "_raw"
New-Item -ItemType Directory -Force -Path $raw | Out-Null

$items = @(
  @{ name = 'weather_seattle_2016.csv'; min = 400000; urls = @(
      'https://raw.githubusercontent.com/plotly/datasets/master/2016-weather-data-seattle.csv') },
  @{ name = 'meteorites.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/plotly/datasets/master/Meteorite_Landings.csv',
      'https://cdn.jsdelivr.net/gh/plotly/datasets@master/Meteorite_Landings.csv') },
  @{ name = 'global_power_plants.csv'; min = 500000; urls = @(
      'https://raw.githubusercontent.com/plotly/datasets/master/global_power_plant_database.csv',
      'https://cdn.jsdelivr.net/gh/plotly/datasets@master/global_power_plant_database.csv') },
  @{ name = 'china_region_codes.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/modood/Administrative-divisions-of-China/master/dist/pcas-code.json',
      'https://cdn.jsdelivr.net/gh/modood/Administrative-divisions-of-China@master/dist/pcas-code.json') },
  @{ name = 'superstore.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/leonism/sample-superstore/master/data/superstore.csv',
      'https://cdn.jsdelivr.net/gh/leonism/sample-superstore@master/data/superstore.csv') },
  @{ name = 'sales_data_sample.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/rashida048/Datasets/master/sales_data_sample.csv',
      'https://cdn.jsdelivr.net/gh/rashida048/Datasets@master/sales_data_sample.csv') },
  @{ name = 'chinook.sql'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql',
      'https://cdn.jsdelivr.net/gh/lerocha/chinook-database@master/ChinookDatabase/DataSources/Chinook_Sqlite.sql') },
  @{ name = 'olist_orders_dataset.csv'; min = 1000000; urls = @(
      'https://raw.githubusercontent.com/olistbr/brazilian-ecommerce/master/olist_orders_dataset.csv') },
  @{ name = 'olist_customers_dataset.csv'; min = 1000000; urls = @(
      'https://raw.githubusercontent.com/olistbr/brazilian-ecommerce/master/olist_customers_dataset.csv') },
  @{ name = 'olist_order_items_dataset.csv'; min = 1000000; urls = @(
      'https://raw.githubusercontent.com/olistbr/brazilian-ecommerce/master/olist_order_items_dataset.csv') },
  @{ name = 'olist_products_dataset.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/olistbr/brazilian-ecommerce/master/olist_products_dataset.csv') },
  @{ name = 'olist_order_payments_dataset.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/olistbr/brazilian-ecommerce/master/olist_order_payments_dataset.csv') },
  @{ name = 'olist_order_reviews_dataset.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/olistbr/brazilian-ecommerce/master/olist_order_reviews_dataset.csv') },
  @{ name = 'olist_sellers_dataset.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/olistbr/brazilian-ecommerce/master/olist_sellers_dataset.csv') },
  @{ name = 'olist_product_category_name_translation.csv'; min = 1000; urls = @(
      'https://raw.githubusercontent.com/olistbr/brazilian-ecommerce/master/olist_product_category_name_translation.csv') },
  @{ name = 'wiki_movie_plots.csv'; min = 1000000; urls = @(
      'https://raw.githubusercontent.com/jrobischon/wikipedia-movie-plots/master/wiki_movie_plots_deduped.csv') },
  @{ name = 'bank_marketing.csv'; min = 500000; urls = @(
      'https://raw.githubusercontent.com/selva86/datasets/master/bank-full.csv',
      'https://cdn.jsdelivr.net/gh/selva86/datasets@master/bank-full.csv') },
  @{ name = 'hr_analytics.csv'; min = 10000; urls = @(
      'https://raw.githubusercontent.com/plotly/datasets/master/HR_comma_sep.csv',
      'https://cdn.jsdelivr.net/gh/plotly/datasets@master/HR_comma_sep.csv') }
)

$report = @()
foreach ($it in $items) {
  $out = Join-Path $raw $it.name
  if ((Test-Path $out) -and ((Get-Item $out).Length -ge $it.min)) {
    Write-Output ("[skip] {0}" -f $it.name)
    $report += [pscustomobject]@{ file=$it.name; status='cached'; src='(cached)'; bytes=(Get-Item $out).Length }
    continue
  }
  $got = $false
  foreach ($u in $it.urls) {
    if (Test-Path $out) { Remove-Item $out -Force }
    $curlArgs = @('-sS','-L','--retry','1','--connect-timeout','20','--max-time','600',
                  '--speed-limit','2000','--speed-time','30','-o',$out,'-w','%{http_code}',$u)
    $code = (& curl.exe @curlArgs 2>&1) -join ''
    $sz = if (Test-Path $out) { (Get-Item $out).Length } else { 0 }
    if ($code -eq '200' -and $sz -ge $it.min) {
      Write-Output ("[ok]   {0,-46} {1,10:N0} bytes" -f $it.name, $sz)
      $report += [pscustomobject]@{ file=$it.name; status='ok'; src=$u; bytes=$sz }
      $got = $true; break
    }
    Write-Output ("[fail] {0,-46} http={1} bytes={2}" -f $it.name, $code, $sz)
  }
  if (-not $got) { $report += [pscustomobject]@{ file=$it.name; status='FAILED'; src=($it.urls -join ' | '); bytes=0 } }
}
$report | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $raw "_download-report2.json") -Encoding UTF8
Write-Output "=== summary ==="
$report | Group-Object status | ForEach-Object { "{0}: {1}" -f $_.Name, $_.Count }
