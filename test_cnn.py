#!/usr/bin/env python3
"""Test script for CNN-based classification pipeline"""

from backend.main import EDNAModel
import json

# Initialize model with CNN pipeline
print('='*70)
print('Initializing model with CNN pipeline...')
print('='*70)
model = EDNAModel()

# Test with oyster sequence (should match Crassostrea gigas, NOT Delphinus)
oyster_seq = 'ATGACAACTCTGACACCCGACGAAGTCTATGTGCTGCTGCTGGGCGGACTGGGAGACACGGATGTGCTGGTACTCCTGCTGCTGTATACCGAAGGCGACGAAGTGAAGTTCCCGTTCCTGCTGCTGCACACCGGCACCGGTACCCCGGTGCTGGTACTACCCGACGTTGGTCGCATGGGCGACAGAGAAGGACTGAAGTGCCTGGATGAGGTCAAAGTTATTATTTATGTGACCCTGCTGGCCCGCGGACAAGTTGTACGTACTGGTACCGCAGTACATCGATAAA'

print('\n' + '='*70)
print('TEST 1: Oyster sequence classification')
print('='*70)
result = model.predict(oyster_seq)
print(f'\nTop match: {result["species"]} ({result["confidence"]}% confidence)')
print(f'Status: Novel={result.get("is_novel")}, Match={result.get("is_match")}, Uncertain={result.get("is_uncertain")}')
print(f'\nScores (all species):')
for sp, score in sorted(result.get("scores", {}).items(), key=lambda x: x[1], reverse=True):
    print(f'  {sp}: {score}%')

print(f'\nMethod: {result.get("method")}')
print(f'Description: {result.get("description")}')
