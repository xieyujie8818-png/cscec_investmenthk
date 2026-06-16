$files = @(
  "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_pe.html",
  "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_home.html"
)
$out = @()
foreach ($file in $files) {
  $text = [IO.File]::ReadAllText($file)
  $out += "FILE: $file"
  # extract quoted strings containing digits and HK or $
  $matches = [regex]::Matches($text, '"A":"([^"\\]{1,200})"')
  foreach ($m in $matches) {
    $s = $m.Groups[1].Value -replace '\\n',' '
    if ($s -match '(?i)(HK|\$|rent|month|3800|11800|9900|10800|8800|11,?800|3,?800|price|fee)') {
      $out += $s
    }
  }
}
$out | Select-Object -Unique | Set-Content "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_strings.txt" -Encoding UTF8
