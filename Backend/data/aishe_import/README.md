# Institution registry data

| File | Source | Loaded by |
|---|---|---|
| `haryana_institutions_raw.json` (+ `_review.csv`, `_import_audit.md`) | DHE Centralized Online Scholarship registry PDF: 1,152 institutions with DHE institute codes; 71 have no AISHE code | `import_haryana_institutions` |
| `aishe_haryana_registry.json` | AISHE portal exports, as on 17-10-2026 (`docs/*.xlsx`): 1,241 colleges, 382 standalone institutions, 60 universities, all in Haryana; 42 also appear in the PM Vidyalaxmi list | `import_aishe_registry` |
| `aishe_dhe_links.csv` | DHE records whose AISHE code is blank or wrong in the DHE PDF, matched to the AISHE list. `confirmed` rows are applied; `suggested` rows are only applied after someone verifies them and changes the status to `confirmed` | `import_aishe_registry` |

## Load order (every environment)

```
python manage.py import_haryana_institutions
python manage.py import_aishe_registry            # --dry-run to preview
```

Run `import_aishe_registry` again after any re-run of `import_haryana_institutions`, which resets the AISHE codes that the link file corrected.

`import_aishe_registry` never renames or deletes DHE records. It adds every AISHE code that is not yet registered as a new College (codes starting `C-` or `S-`) or University (`U-`), with no DHE institute code. It keeps the rows it created up to date with the list. It lists DHE AISHE codes that are not in the AISHE list (`-v 2`) but leaves them unchanged.

## Refreshing the AISHE list

1. Download the four reports from the AISHE portal into `docs/`, keeping the same file names.
2. Rebuild the JSON and load it:

```
pip install openpyxl                               # development only
python manage.py build_aishe_registry              # --xlsx-dir <dir> if the files are elsewhere
python manage.py import_aishe_registry --dry-run
python manage.py import_aishe_registry
```
