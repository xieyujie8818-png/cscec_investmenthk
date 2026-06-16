$text = [IO.File]::ReadAllText("C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_home.html")
$idx = $text.IndexOf('monthly rent')
if ($idx -ge 0) {
  $text.Substring([Math]::Max(0,$idx-200), 600) | Set-Content "C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\asquare_faq_snip.txt"
}
