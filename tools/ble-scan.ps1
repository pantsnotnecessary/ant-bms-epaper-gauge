[Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementWatcher, Windows.Devices.Bluetooth, ContentType=WindowsRuntime] | Out-Null

$watcher = New-Object Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementWatcher
$watcher.ScanningMode = [Windows.Devices.Bluetooth.Advertisement.BluetoothLEScanningMode]::Active

$results = [System.Collections.Concurrent.ConcurrentBag[string]]::new()

$watcher.add_Received({
    param($s, $e)
    $addr = $e.BluetoothAddress
    $mac = "{0:X2}:{1:X2}:{2:X2}:{3:X2}:{4:X2}:{5:X2}" -f `
        (($addr -shr 40) -band 0xFF), (($addr -shr 32) -band 0xFF),
        (($addr -shr 24) -band 0xFF), (($addr -shr 16) -band 0xFF),
        (($addr -shr 8)  -band 0xFF),  ($addr -band 0xFF)
    $name = $e.Advertisement.LocalName
    $label = if ($name) { $name } else { "(no name)" }
    $results.Add("$mac  $label")
}) | Out-Null

$watcher.Start()
Write-Host "Scanning for 30 seconds... wake BMS with ANT app then close it."
Start-Sleep -Seconds 30
$watcher.Stop()

Write-Host "`nResults:"
$results | Sort-Object -Unique | ForEach-Object { Write-Host $_ }
Write-Host "Total unique entries: $($($results | Sort-Object -Unique).Count)"
