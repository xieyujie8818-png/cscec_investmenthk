foreach ($file in @(
  "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_home.html",
  "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_pe.html"
)) {
  $text = [IO.File]::ReadAllText($file)
  $matches = [regex]::Matches($text, '\\"A\\":\\"([^\\"]{2,300})\\"')
  $out = @("=== $file ===")
  foreach ($m in $matches) {
    $s = $m.Groups[1].Value -replace '\\n',' ' -replace '\\u0024','$'
    if ($s -match '(?i)(rent|month|HK|fee|water|electric|single|twin|quad|sextuple|studio|price|\$\s*\d|\d{4,5})') {
      $out += $s
    }
  }
  $out | Add-Content "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_all_text.txt" -Encoding UTF8
}
