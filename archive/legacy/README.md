# Legacy Code Archive

**Purpose:** Archive deprecated, duplicate, or misorganized code instead of permanently deleting it.

**Policy:** When removing code due to organization issues, move it to `archive/legacy/` with a README explaining:
- Why it was archived
- What replaced it
- Migration instructions

---

## Archived Items

### 2025-11-05

#### 1. `calibration/imaging.py` → `archive/legacy/calibration/imaging.py`
- **Reason:** Misplaced module - imaging functionality belongs in `imaging/` package
- **Replacement:** Use `imaging/cli.py` `image_ms()` function with `quick=True`
- **See:** `archive/legacy/calibration/imaging.py.README.md` for details

#### 2. `utils/data/DSA110_Station_Coordinates.csv` → `archive/legacy/utils/data/`
- **Reason:** Duplicate antenna coordinate data file
- **Replacement:** Use `utils/antpos_local/data/DSA110_Station_Coordinates.csv`
- **See:** `archive/legacy/utils/data/README.md` for details

#### 3. `calibration/qa.py` → `archive/legacy/calibration/qa.py`
- **Reason:** Consolidated with `qa/calibration_quality.py` for better organization
- **Replacement:** Use `qa/calibration_quality.py` for delay QA functions
- **See:** `archive/legacy/calibration/qa.py.README.md` for details

---

## Archive Structure

```
archive/legacy/
├── calibration/
│   ├── imaging.py                    # Archived imaging function
│   └── imaging.py.README.md          # Migration guide
├── utils/
│   └── data/
│       ├── DSA110_Station_Coordinates.csv  # Archived duplicate CSV
│       └── README.md                        # Migration guide
└── README.md                         # This file
```

---

## Archive Policy

1. **Never delete** - Always archive to `archive/legacy/`
2. **Document** - Include README explaining why and how to migrate
3. **Update imports** - Update all code that used the archived items
4. **Test** - Verify updated code works before archiving

---

## Finding Archived Code

If you need archived code:
1. Check `archive/legacy/` for the file
2. Read the corresponding README.md for migration instructions
3. Use the replacement functionality instead when possible
