# Local data directory

The application creates its SQLite database here when run. Database files and
other generated outputs are intentionally ignored by Git.

For optional CSV ingestion, obtain the synthetic assignment dataset
separately and place its required CSV files under `raw/`. The `raw/` directory
is ignored because it contains borrower contact columns and may contain
personal data in other distributions. Do not put real borrower information in
this repository. Ingestion writes its summary under `cleaned/`; that output is
also local-only.

The repository does not include the dataset or a pre-populated database.
