# Delphinus Multi-Source Results

| ID | Source Group | Source Name | Label Hint | Predicted Species | Confidence | Match | Uncertain | Novel | Len | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | uploaded_zip | ncbi_dataset.zip:gene.fna | Delphinus delphis | Delphinus delphis | 98.08 | True | False | False | 1541 | tested |
| 2 | workspace_extract | _ncbi_extract/ncbi_dataset/data/gene.fna | Delphinus delphis | Delphinus delphis | 98.08 | True | False | False | 1541 | tested |
| 3 | ncbi_accession | NCBI accession EF090639.1 (FASTA) | Delphinus delphis | Delphinus delphis | 92.75 | True | False | False | 756 | tested |
| 4 | ncbi_accession | NCBI accession NC_012061.1 (FASTA) | Delphinus capensis | Putative novel / unrecognised species | 0.0 | False | False | True | 16385 | tested |
| 5 | ncbi_accession | NCBI accession NC_012053.1 (FASTA) | Stenella coeruleoalba | Putative novel / unrecognised species | 0.0 | False | False | True | 16384 | tested |
| 6 | ncbi_esearch | NCBI esearch Delphinus delphis | Delphinus delphis | Delphinus delphis | 92.75 | True | False | False | 756 | tested |
| 7 | ncbi_esearch | NCBI esearch Delphinus delphis | Delphinus delphis | Delphinus delphis | 93.18 | True | False | False | 756 | tested |
| 8 | ncbi_esearch | NCBI esearch Delphinus delphis | Delphinus delphis | Putative novel / unrecognised species | 0.0 | False | False | True | 4672 | tested |
| 9 | ncbi_esearch | NCBI esearch Delphinus capensis | Delphinus capensis | Putative novel / unrecognised species | 0.0 | False | False | True | 16385 | tested |
| 10 | ncbi_esearch | NCBI esearch Delphinus capensis | Delphinus capensis | Putative novel / unrecognised species | 0.0 | False | False | True | 16385 | tested |
| 11 | ncbi_esearch | NCBI esearch Delphinus capensis | Delphinus capensis | Delphinus delphis | 92.36 | True | False | False | 686 | tested |
| 12 | model_reference | backend fallback reference | Delphinus delphis | Delphinus delphis | 100.0 | True | False | False | 282 | tested |

## Summary

- total_rows: 12
- tested_rows: 12
- error_rows: 0
- predicted_species_counts: {'Delphinus delphis': 7, 'Putative novel / unrecognised species': 5}
- tested_by_source_group: {'uploaded_zip': 1, 'workspace_extract': 1, 'ncbi_accession': 3, 'ncbi_esearch': 6, 'model_reference': 1}
- novel_count: 5
- match_count: 7
- uncertain_count: 0
