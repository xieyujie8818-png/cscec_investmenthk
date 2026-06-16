$ErrorActionPreference = "Stop"
$dir = $PSScriptRoot
$path = (Get-ChildItem -Path $dir -Filter "*2021-2026.xls" | Where-Object { $_.Name -notlike "_*" } | Select-Object -First 1).FullName
$backup = Join-Path $dir "_may_filled.xls"

$rows = @(
    @{ Row = 6;  Range = 'HK$22,114 - HK$23,249'; Avg = 22457; Vol = 92 }
    @{ Row = 7;  Range = ''; Avg = $null; Vol = $null }
    @{ Row = 8;  Range = 'HK$33,987 - HK$36,744'; Avg = 35431; Vol = 29 }
    @{ Row = 9;  Range = 'HK$42,019 - HK$45,074'; Avg = 43966; Vol = 5 }
    @{ Row = 10; Range = 'HK$23,932'; Avg = 23932; Vol = 28 }
    @{ Row = 11; Range = 'HK$20,725'; Avg = 20725; Vol = 14 }
    @{ Row = 12; Range = 'HK$28,670'; Avg = 28670; Vol = 4 }
    @{ Row = 13; Range = 'HK$23,159 - HK$26,663'; Avg = 24487; Vol = 18 }
    @{ Row = 14; Range = 'HK$28,906'; Avg = 28906; Vol = 13 }
    @{ Row = 15; Range = 'HK$41,452'; Avg = 41452; Vol = 12 }
)

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$wb = $excel.Workbooks.Open($path)
$ws = $wb.Worksheets.Item(1)

foreach ($item in $rows) {
    $rangeCell = $ws.Cells.Item($item.Row, 16)
    $avgCell = $ws.Cells.Item($item.Row, 17)
    $volCell = $ws.Cells.Item($item.Row, 19)

    if ($item.Range) { $rangeCell.Value2 = [string]$item.Range } else { $rangeCell.ClearContents() }

    if ($null -ne $item.Avg) {
        $avgCell.ClearContents()
        $avgCell.Value2 = [double]$item.Avg
        $avgCell.NumberFormat = "#,##0"
    } else {
        $avgCell.ClearContents()
    }

    if ($null -ne $item.Vol) {
        $volCell.ClearContents()
        $volCell.Value2 = [double]$item.Vol
        $volCell.NumberFormat = "0"
    } else {
        $volCell.ClearContents()
    }
}

# xlExcel8 = 56 for .xls
if (Test-Path $backup) { Remove-Item $backup -Force }
$wb.SaveAs($backup, 56)
$wb.Close($false)
$excel.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null

$outCopy = Join-Path $dir "runway_may_updated.xls"
Copy-Item -Path $backup -Destination $outCopy -Force
try {
    Copy-Item -Path $backup -Destination $path -Force -ErrorAction Stop
    Remove-Item $outCopy -Force -ErrorAction SilentlyContinue
    Write-Output ("Updated original: " + $path)
} catch {
    Write-Warning "Original file is locked - close Excel/WPS then run script again, or use:"
    Write-Output $outCopy
}
