$text = [IO.File]::ReadAllText("C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_pe.html")
$patterns = @(
  'Single Room',
  '11800',
  '11,800',
  '3800',
  '3,800',
  'HK\$',
  'monthly',
  'Monthly',
  'Rent',
  'Signle room',
  'Sextuple',
  'Twin Room'
)
$out = @()
foreach ($p in $patterns) {
  $idx = 0
  while (($idx = $text.IndexOf($p, $idx)) -ge 0) {
    $start = [Math]::Max(0, $idx - 120)
    $len = [Math]::Min(280, $text.Length - $start)
    $out += "=== $p @ $idx ==="
    $out += $text.Substring($start, $len)
    $idx += $p.Length
    if ($out.Count -gt 80) { break }
  }
}
$out | Set-Content "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_extract.txt" -Encoding UTF8
