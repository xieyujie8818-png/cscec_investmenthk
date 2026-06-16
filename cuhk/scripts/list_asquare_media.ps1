$text = [IO.File]::ReadAllText("C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_home.html")
$matches = [regex]::Matches($text, '_assets/media/([a-f0-9]+\.(?:png|jpg|jpeg))')
$urls = $matches | ForEach-Object { $_.Value } | Select-Object -Unique
$urls | Set-Content "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_media_urls.txt"
"count=$($urls.Count)"
