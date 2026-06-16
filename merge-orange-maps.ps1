Add-Type -AssemblyName System.Drawing

function Get-BitmapBytes($bitmap) {
    $rect = New-Object System.Drawing.Rectangle 0, 0, $bitmap.Width, $bitmap.Height
    $data = $bitmap.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $stride = $data.Stride
    $bytes = New-Object byte[] ($stride * $bitmap.Height)
    [System.Runtime.InteropServices.Marshal]::Copy($data.Scan0, $bytes, 0, $bytes.Length)
    $bitmap.UnlockBits($data)
    return @{ Bytes = $bytes; Stride = $stride; Width = $bitmap.Width; Height = $bitmap.Height }
}

function Test-OrangeAt($bytes, $stride, $x, $y) {
    $idx = $y * $stride + $x * 3
    $b = $bytes[$idx]
    $g = $bytes[$idx + 1]
    $r = $bytes[$idx + 2]
    return ($r -ge 200 -and $g -ge 50 -and $g -le 110 -and $b -le 80 -and ($r - $g) -ge 100)
}

function Get-ColorAt($bytes, $stride, $x, $y) {
    $idx = $y * $stride + $x * 3
    return @($bytes[$idx + 2], $bytes[$idx + 1], $bytes[$idx])
}

function Set-ColorAt($bytes, $stride, $x, $y, $r, $g, $b) {
    $idx = $y * $stride + $x * 3
    $bytes[$idx] = [byte]$b
    $bytes[$idx + 1] = [byte]$g
    $bytes[$idx + 2] = [byte]$r
}

function Save-BitmapBytes($width, $height, $bytes, $srcStride, $path) {
    $bmp = New-Object System.Drawing.Bitmap $width, $height
    $rect = New-Object System.Drawing.Rectangle 0, 0, $width, $height
    $fmt = [System.Drawing.Imaging.PixelFormat]::Format24bppRgb
    $data = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::WriteOnly, $fmt)
    $dstStride = $data.Stride
    $dstBytes = New-Object byte[] ($dstStride * $height)
    for ($y = 0; $y -lt $height; $y++) {
        $srcRow = $y * $srcStride
        $dstRow = $y * $dstStride
        for ($x = 0; $x -lt $width; $x++) {
            $si = $srcRow + $x * 3
            $di = $dstRow + $x * 3
            $dstBytes[$di] = $bytes[$si]
            $dstBytes[$di + 1] = $bytes[$si + 1]
            $dstBytes[$di + 2] = $bytes[$si + 2]
        }
    }
    [System.Runtime.InteropServices.Marshal]::Copy($dstBytes, 0, $data.Scan0, $dstBytes.Length)
    $bmp.UnlockBits($data)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}

$assets = "C:\Users\yujie.xie\.cursor\projects\c-Users-yujie-xie-cursor-cohl-marketing\assets"
$outDir = "C:\Users\yujie.xie\.cursor\cohl-marketing\output"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$imageFiles = @(
    (Get-ChildItem $assets -Filter "*2b02cfef*").FullName,
    (Get-ChildItem $assets -Filter "*fcb83be1*").FullName,
    (Get-ChildItem $assets -Filter "*f713b0d2*").FullName,
    (Get-ChildItem $assets -Filter "*b64bf469*").FullName,
    (Get-ChildItem $assets -Filter "*4c2ac537*").FullName
)

$layers = @()
$bitmaps = @()
foreach ($path in $imageFiles) {
    $bmp = [System.Drawing.Bitmap]::FromFile($path)
    $bitmaps += $bmp
    $layers += Get-BitmapBytes $bmp
}

$width = $layers[0].Width
$height = $layers[0].Height
$outStride = [int][Math]::Ceiling($width * 3 / 4) * 4
$outBytes = New-Object byte[] ($outStride * $height)

$orangeR = 240
$orangeG = 79
$orangeB = 35
$orangeCount = 0

for ($y = 0; $y -lt $height; $y++) {
    for ($x = 0; $x -lt $width; $x++) {
        $isOrange = $false
        $base = $null

        foreach ($layer in $layers) {
            if (Test-OrangeAt $layer.Bytes $layer.Stride $x $y) {
                $isOrange = $true
            } elseif ($null -eq $base) {
                $base = Get-ColorAt $layer.Bytes $layer.Stride $x $y
            }
        }

        if ($isOrange) {
            Set-ColorAt $outBytes $outStride $x $y $orangeR $orangeG $orangeB
            $orangeCount++
        } elseif ($null -ne $base) {
            Set-ColorAt $outBytes $outStride $x $y $base[0] $base[1] $base[2]
        }
    }
}

$outPath = Join-Path $outDir "combined-phase2-orange.png"
Save-BitmapBytes $width $height $outBytes $outStride $outPath

foreach ($bmp in $bitmaps) { $bmp.Dispose() }

Write-Output "Saved: $outPath"
Write-Output "Combined orange pixels: $orangeCount"
