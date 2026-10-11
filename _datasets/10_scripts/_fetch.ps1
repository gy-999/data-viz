# data-viz demo data fetcher: try mirrors in order, hard timeouts, skip failures instead of hanging.
# No line-continuation backticks on purpose (a trailing space there breaks parsing).
$ErrorActionPreference = 'Continue'
$root = "D:\Claude cade\data\_datasets"
$raw  = Join-Path $root "_raw"
New-Item -ItemType Directory -Force -Path $raw | Out-Null

$items = @(
  @{ name = 'ml-latest-small.zip'; min = 100000; urls = @(
      'https://files.grouplens.org/datasets/movielens/ml-latest-small.zip') },
  @{ name = 'gapminder.csv'; min = 50000; urls = @(
      'https://cdn.jsdelivr.net/gh/plotly/datasets@master/gapminderDataFiveYear.csv',
      'https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv') },
  @{ name = 'finance-charts-apple.csv'; min = 10000; urls = @(
      'https://cdn.jsdelivr.net/gh/plotly/datasets@master/finance-charts-apple.csv') },
  @{ name = 'titanic.csv'; min = 30000; urls = @(
      'https://cdn.jsdelivr.net/gh/datasciencedojo/datasets@master/titanic.csv',
      'https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv') },
  @{ name = 'wiki_movie_plots.csv'; min = 1000000; urls = @(
      'https://cdn.jsdelivr.net/gh/jrobischon/wikipedia-movie-plots@master/wiki_movie_plots_deduped.csv',
      'https://raw.githubusercontent.com/jrobischon/wikipedia-movie-plots/master/wiki_movie_plots_deduped.csv') },
  @{ name = 'earthquakes_2024.csv'; min = 50000; urls = @(
      'https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime=2024-01-01&endtime=2024-12-31&minmagnitude=4') },
  @{ name = 'olist_customers_dataset.csv'; min = 1000000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_customers_dataset.csv') },
  @{ name = 'olist_orders_dataset.csv'; min = 1000000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_orders_dataset.csv') },
  @{ name = 'olist_order_items_dataset.csv'; min = 1000000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_order_items_dataset.csv') },
  @{ name = 'olist_products_dataset.csv'; min = 100000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_products_dataset.csv') },
  @{ name = 'olist_order_payments_dataset.csv'; min = 100000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_order_payments_dataset.csv') },
  @{ name = 'olist_order_reviews_dataset.csv'; min = 100000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_order_reviews_dataset.csv') },
  @{ name = 'olist_sellers_dataset.csv'; min = 100000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_sellers_dataset.csv') },
  @{ name = 'olist_geolocation_dataset.csv'; min = 1000000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_geolocation_dataset.csv') },
  @{ name = 'olist_product_category_name_translation.csv'; min = 1000; urls = @(
      'https://cdn.jsdelivr.net/gh/olistbr/brazilian-ecommerce@master/olist_product_category_name_translation.csv') },
  @{ name = 'taxis.csv'; min = 10000; urls = @(
      'https://raw.githubusercontent.com/mwaskom/seaborn-data/master/taxis.csv',
      'https://cdn.jsdelivr.net/gh/mwaskom/seaborn-data@master/taxis.csv') },
  @{ name = 'penguins.csv'; min = 5000; urls = @(
      'https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv',
      'https://cdn.jsdelivr.net/gh/mwaskom/seaborn-data@master/penguins.csv') },
  @{ name = 'iris.csv'; min = 3000; urls = @(
      'https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv',
      'https://cdn.jsdelivr.net/gh/mwaskom/seaborn-data@master/iris.csv') },
  @{ name = 'diamonds.csv'; min = 100000; urls = @(
      'https://raw.githubusercontent.com/mwaskom/seaborn-data/master/diamonds.csv',
      'https://cdn.jsdelivr.net/gh/mwaskom/seaborn-data@master/diamonds.csv') }
)

$report = @()
foreach ($it in $items) {
  $out = Join-Path $raw $it.name
  if ((Test-Path $out) -and ((Get-Item $out).Length -ge $it.min)) {
    Write-Output ("[skip] {0} (cached {1:N0} bytes)" -f $it.name, (Get-Item $out).Length)
    $report += [pscustomobject]@{ file = $it.name; status = 'cached'; src = '(cached)'; bytes = (Get-Item $out).Length }
    continue
  }
  $got = $false
  foreach ($u in $it.urls) {
    if (Test-Path $out) { Remove-Item $out -Force }
    $curlArgs = @('-sS', '-L', '--retry', '1', '--connect-timeout', '20', '--max-time', '600',
                  '--speed-limit', '2000', '--speed-time', '30', '-o', $out, '-w', '%{http_code}', $u)
    $code = (& curl.exe @curlArgs 2>&1) -join ''
    $sz = if (Test-Path $out) { (Get-Item $out).Length } else { 0 }
    if ($code -eq '200' -and $sz -ge $it.min) {
      Write-Output ("[ok]   {0,-46} {1,10:N0} bytes" -f $it.name, $sz)
      $report += [pscustomobject]@{ file = $it.name; status = 'ok'; src = $u; bytes = $sz }
      $got = $true
      break
    }
    Write-Output ("[fail] {0,-46} http={1} bytes={2}" -f $it.name, $code, $sz)
  }
  if (-not $got) { $report += [pscustomobject]@{ file = $it.name; status = 'FAILED'; src = ($it.urls -join ' | '); bytes = 0 } }
}
$report | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $raw "_download-report.json") -Encoding UTF8
Write-Output "=== summary ==="
$report | Group-Object status | ForEach-Object { "{0}: {1}" -f $_.Name, $_.Count }
Write-Output ("total: {0:N1} MB" -f ((Get-ChildItem $raw -File | Measure-Object Length -Sum).Sum / 1MB))
