# coverage-gap rubric

| condition | severity | confidence | meaning |
|---|---|---|---|
| file absent from all reports, or 0 executed lines | high | high | untested file |
| 0% < percent < min_file_coverage (default 50%) | medium | medium | under-tested file |
| percent >= min_file_coverage | — | — | no finding |

Merge rule across multiple `--coverage-json` reports: executed lines = union;
`num_statements` = max; files with 0 statements count as 100% covered.
Percent = `round(100 * |executed| / num_statements, 2)`.
Signal is always `TEST`; symbol is always `<file>`; line range is `1..1`.
