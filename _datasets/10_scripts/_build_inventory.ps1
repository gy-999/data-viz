# Build the local media/document inventory folder for the data-viz skill demo.
$ErrorActionPreference = 'Continue'
$inv = "D:\Claude cade\data\_datasets\04_media_inventory"
$img = Join-Path $inv "images"; $vid = Join-Path $inv "video"; $doc = Join-Path $inv "docs"; $arc = Join-Path $inv "archives"
foreach ($d in @($img, $vid, $doc, $arc)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

$sources = @("D:\Claude cade\data", "D:\Claude cade\skill", "C:\Users\guoyu\Downloads", "C:\Users\guoyu\Documents")
$all = foreach ($s in $sources) { Get-ChildItem -LiteralPath $s -Recurse -File -ErrorAction SilentlyContinue }

$imgExt = '^\.(jpg|jpeg|png|gif|bmp|webp|livp)$'
$vidExt = '^\.(mp4|mov|avi|mkv)$'
$docExt = '^\.(docx|doc|pptx|xlsx|xls|pdf)$'
$arcExt = '^\.zip$'

# Skip the inventory itself so a re-run does not copy its own output.
$all = $all | Where-Object { $_.FullName -notlike "$inv*" }

$index = @()
$i = 0
foreach ($f in $all) {
  $i++
  $ext = $f.Extension.ToLower()
  $target = $null; $kind = $null
  if ($ext -match $imgExt) { $target = $img; $kind = 'image' }
  elseif ($ext -match $vidExt) { $target = $vid; $kind = 'video' }
  elseif ($ext -match $docExt) { $target = $doc; $kind = 'document' }
  elseif ($ext -match $arcExt) { $target = $arc; $kind = 'archive' }
  if (-not $target) { continue }
  $short = $f.Name
  if ($short.Length -gt 90) { $short = $f.BaseName.Substring(0, [Math]::Min(80, $f.BaseName.Length)) + $ext }
  $dest = Join-Path $target ("{0:0000}_{1}" -f $i, $short)
  try { Copy-Item -LiteralPath $f.FullName -Destination $dest -Force -ErrorAction Stop }
  catch { Write-Output ("[skip] {0}: {1}" -f $f.FullName, $_.Exception.Message); continue }
  $index += [pscustomobject]@{
    file      = (Split-Path $dest -Leaf)
    kind      = $kind
    ext       = $ext
    bytes     = $f.Length
    source    = $f.FullName
    modified  = $f.LastWriteTime.ToString('yyyy-MM-dd')
  }
}
$index | Export-Csv -Path (Join-Path $inv "index.csv") -NoTypeInformation -Encoding UTF8
Write-Output "=== inventory built ==="
foreach ($d in @($img, $vid, $doc, $arc)) {
  $fs = Get-ChildItem $d -File -ErrorAction SilentlyContinue
  Write-Output ("{0,-10} {1,5} files  {2,9:N1} MB" -f (Split-Path $d -Leaf), $fs.Count, (($fs | Measure-Object Length -Sum).Sum / 1MB))
}
Write-Output ("index.csv rows: {0}" -f $index.Count)
# duplicates by content hash are the interesting part for media_probe; report what we have locally
$dups = $index | Group-Object { (Get-FileHash (Join-Path $inv ("images\" + $_.file)) -Algorithm MD5 -ErrorAction SilentlyContinue).Hash } |
        Where-Object { $_.Name -and $_.Count -gt 1 }
Write-Output ("exact-duplicate image groups: {0}" -f @($dups).Count)
