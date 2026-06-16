Add-Type -AssemblyName System.Drawing
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$inputPath = "C:\Users\yujie.xie\.cursor\cohl-marketing\output\combined-phase2-orange.png"
$outputPath = $inputPath
$tempPath = "$outputPath.tmp.png"
$labelLine1Path = "C:\Users\yujie.xie\.cursor\cohl-marketing\output\label-line1.txt"
$labelLine2Path = "C:\Users\yujie.xie\.cursor\cohl-marketing\output\label-line2.txt"

$src = [System.Drawing.Bitmap]::FromFile($inputPath)
$bmp = $src.Clone()
$src.Dispose()

$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

$bgColor = [System.Drawing.Color]::FromArgb(245, 250, 253)
$bgBrush = New-Object System.Drawing.SolidBrush $bgColor
$orangeBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 240, 79, 35))
$textBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(0, 0, 0))

# Clear Phase 1 + old Phase 2 legend rows (keep boundary row)
$graphics.FillRectangle($bgBrush, 385, 26, 160, 62)

# Phase 2 orange swatch
$graphics.FillRectangle($orangeBrush, 394, 32, 52, 10)

$utf8 = [System.Text.Encoding]::UTF8
$line1 = [System.IO.File]::ReadAllText($labelLine1Path, $utf8).Trim()
$line2 = [System.IO.File]::ReadAllText($labelLine2Path, $utf8).Trim()
$font = New-Object System.Drawing.Font "Microsoft JhengHei", 6.5
$graphics.DrawString($line1, $font, $textBrush, 393.0, 44.0)
$graphics.DrawString($line2, $font, $textBrush, 393.0, 54.0)

$font.Dispose()
$bgBrush.Dispose()
$orangeBrush.Dispose()
$textBrush.Dispose()
$graphics.Dispose()

$bmp.Save($tempPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Move-Item -Force $tempPath $outputPath

Write-Output "Updated: $outputPath"
Write-Output "Label: $line1 $line2"
