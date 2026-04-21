#!/usr/bin/env powershell
# Test script to verify CNN + Cosine Similarity classification improvements
# Tests oyster (Crassostrea) sequence against all species

Write-Host "Waiting for backend to initialize..."
Start-Sleep -Seconds 15

Write-Host "`n========================================`n"
Write-Host "TEST: CNN-Based Classification (Cosine Similarity)`n"
Write-Host "========================================`n"

# Oyster sequence - should now match Crassostrea gigas, NOT Delphinus
$oyster_seq = 'ATGACAACTCTGACACCCGACGAAGTCTATGTGCTGCTGCTGGGCGGACTGGGAGACACGGATGTGCTGGTACTCCTGCTGCTGTATACCGAAGGCGACGAAGTGAAGTTCCCGTTCCTGCTGCTGCACACCGGCACCGGTACCCCGGTGCTGGTACTACCCGACGTTGGTCGCATGGGCGACAGAGAAGGACTGAAGTGCCTGGATGAGGTCAAAGTTATTATTTATGTGACCCTGCTGGCCCGCGGACAAGTTGTACGTACTGGTACCGCAGTACATCGATAAA'

$body = @{ sequence = $oyster_seq } | ConvertTo-Json

Write-Host "Testing with oyster (Crassostrea) sequence (286bp)...`n"

try {
    $response = Invoke-WebRequest -Uri http://localhost:8000/predict -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "✓ REQUEST SUCCESSFUL`n"
    Write-Host "Top Match: $($result.species)"
    Write-Host "Confidence: $($result.confidence)%"
    Write-Host "Status: Novel=$($result.is_novel), Match=$($result.is_match), Uncertain=$($result.is_uncertain)`n"
    Write-Host "All Species Scores (CNN Cosine Similarity):"
    Write-Host "============================================"
    
    foreach ($species in ($result.scores | Get-Member -MemberType NoteProperty | Sort-Object { $result.scores.$($_.Name) } -Descending)) {
        $score = $result.scores.($species.Name)
        Write-Host "$($species.Name): $score%"
    }
    
    Write-Host "`nMethod: $($result.method)"
    Write-Host "Description: $($result.description)`n"
    
} catch {
    Write-Host "✗ ERROR: $_"
    Write-Host "Backend may still be initializing. Check logs."
}
