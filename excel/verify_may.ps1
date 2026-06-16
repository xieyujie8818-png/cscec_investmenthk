$backup = (Get-ChildItem -Path $PSScriptRoot -Filter "*2021-2026.xls" | Where-Object { $_.Name -notlike "_*" -and $_.Name -notlike "runway*" } | Select-Object -First 1).FullName
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$wb = $excel.Workbooks.Open($backup)
$ws = $wb.Worksheets.Item(1)
foreach ($r in 6..15) {
    $name = $ws.Cells.Item($r, 1).Text
    $rng = $ws.Cells.Item($r, 16).Text
    $avg = $ws.Cells.Item($r, 17).Text
    $vol = $ws.Cells.Item($r, 19).Text
    Write-Output ("Row $r : $name | range=$rng | avg=$avg | vol=$vol")
}
$wb.Close($false)
$excel.Quit()
