Write-Host "Waiting for backend..."
Start-Sleep -Seconds 10

$oyster_seq = 'ATGACAACTCTGACACCCGACGAAGTCTATGTGCTGCTGCTGGGCGGACTGGGAGACACGGATGTGCTGGTACTCCTGCTGCTGTATACCGAAGGCGACGAAGTGAAGTTCCCGTTCCTGCTGCTGCACACCGGCACCGGTACCCCGGTGCTGGTACTACCCGACGTTGGTCGCATGGGCGACAGAGAAGGACTGAAGTGCCTGGATGAGGTCAAAGTTATTATTTATGTGACCCTGCTGGCCCGCGGACAAGTTGTACGTACTGGTACCGCAGTACATCGATAAA'

$body = @{ sequence = $oyster_seq } | ConvertTo-Json

Write-Host "Testing oyster sequence...`n"

$response = Invoke-WebRequest -Uri http://localhost:8000/predict -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
$result = $response.Content | ConvertFrom-Json

Write-Host "Top Match: $($result.species)"
Write-Host "Confidence: $($result.confidence)%"
Write-Host "Method: $($result.method)`n"

Write-Host "Scores:"
foreach ($species in ($result.scores | Get-Member -MemberType NoteProperty)) {
    Write-Host "  $($species.Name): $($result.scores.($species.Name))%"
}
