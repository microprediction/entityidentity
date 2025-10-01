# Metals Ontology Implementation Prompts

These prompts will guide the systematic implementation of the metals ontology. Each prompt references the `METALS_ONTOLOGY_PLAN.md` document as the authoritative specification.

## Prompt 1: Setup the metals module structure

"Following the architecture described in sections 1 and 5 of METALS_ONTOLOGY_PLAN.md, create the initial directory structure and module files for the metals ontology in entityidentity/metals/. Create:
- `__init__.py` with module exports
- `metalapi.py` with the public API functions from section 5 (load_metals, metal_identifier, match_metal, list_metals)
- `metalidentity.py` with resolve_metal and topk_matches functions per section 6
- `metalnormalize.py` with the three normalization functions from section 7
- `data/` directory structure as specified in section 1

Follow the functional, DataFrame-first pattern from entityidentity/countries/. Reference METALS_ONTOLOGY_PLAN.md for exact function signatures and behavior."

## Prompt 2: Create the YAML schemas

"Implement the YAML source files according to sections 2 and 4 of METALS_ONTOLOGY_PLAN.md:
1. Create `data/metals.yaml` with the exact schema shown in section 2, including all fields (name, symbol, metal_key, formula, code, category_bucket, cluster_id, default_unit, default_basis, hs6, pra_hint, aliases, notes, sources)
2. Create `data/supply_chain_clusters.yaml` with the 14 clusters defined in section 4

Start with seed data from section 13: Include Platinum, Gold, Copper, APT (with exact specification from section 2), Ferrochrome, Lithium carbonate, and NdPr. Ensure APT follows the example in the plan with formula, code='WO3', and basis='$/mtu WO3'."

## Prompt 3: Implement the build system

"Create `data/build_metals.py` following the build process in section 11 of METALS_ONTOLOGY_PLAN.md:
1. Load metals.yaml and supply_chain_clusters.yaml
2. Generate metal_id using the exact formula from the plan: sha1(normalize(name) + '|metal')[:16]
3. Expand aliases into alias1...alias10 columns per section 3's Parquet schema
4. Implement validate_basis() from section 9 with the APT/FeCr/precious examples
5. Write metals.parquet with all columns as strings (section 3)
6. Generate validation report for duplicates, missing clusters, unit/basis mismatches

Ensure the Parquet schema exactly matches section 3 of METALS_ONTOLOGY_PLAN.md."

## Prompt 4: Implement core resolution logic

"Complete metalidentity.py following the resolution strategy in section 6 of METALS_ONTOLOGY_PLAN.md:
1. Implement the 5-step blocking strategy: exact symbol, category bucket, name prefix (3 chars), optional cluster filter, RapidFuzz scoring
2. Use RapidFuzz process.extractOne with fuzz.WRatio scorer as specified
3. Check aliases (alias1-10 columns) in addition to name_norm
4. Parse 'metal:form' suffixes (e.g., 'lithium:carbonate')
5. Implement topk_matches returning scored candidates

Follow the functional approach from entityidentity/countries/. Reference section 6 for the exact blocking sequence."

## Prompt 5: Add PGM and precious metals

"Expand metals.yaml with the PGM complex and precious metals from section 13 of METALS_ONTOLOGY_PLAN.md:
- All 6 PGM metals: Platinum, Palladium, Rhodium, Ruthenium, Iridium, Osmium (cluster: pgm_complex)
- Gold, Silver (category: precious, appropriate clusters per section 4)

Follow section 10's source priority (IUPAC for element symbols). Include:
- Proper IUPAC symbols
- Common aliases (e.g., 'Pt', 'Pd')
- Default unit='toz' for precious metals
- category_bucket='pgm' for PGMs, 'precious' for Au/Ag"

## Prompt 6: Add base metals and copper chain

"Add metals from the porphyry copper and lead-zinc chains per sections 4 and 13 of METALS_ONTOLOGY_PLAN.md:
1. Porphyry copper chain: Copper, Molybdenum, Rhenium (by-product), Selenium, Tellurium (from anode slimes)
2. Lead-zinc chain: Zinc, Lead, Cadmium, Indium (from Zn residues), Germanium, Bismuth, Antimony

Include:
- Correct cluster_id assignments from section 4
- Commercial forms (SHG zinc, P1020 aluminum) as aliases
- USGS source citations for by-product relationships per section 10
- Notes field documenting recovery routes (e.g., 'Re from Mo roaster flue dust')"

## Prompt 7: Add battery and critical metals

"Add battery metals following sections 2 and 13 of METALS_ONTOLOGY_PLAN.md:
1. Lithium forms with proper formula/code fields:
   - Lithium metal (Li, symbol='Li')
   - Lithium carbonate (formula='Li2CO3', code='Li2CO3')
   - Lithium hydroxide (formula='LiOH·H2O', code='LiOH')
2. Cobalt: metal and sulfate forms
3. Nickel: metal and sulfate forms
4. Graphite (natural and synthetic)

Include:
- category_bucket='battery' for all
- Fastmarkets PRA hints (e.g., MB-CO-0005 for cobalt standard grade per section 2)
- Proper default_unit and default_basis from Fastmarkets references"

## Prompt 8: Add rare earth elements

"Add all REEs from section 13 to metals.yaml following the structure in METALS_ONTOLOGY_PLAN.md:
1. Light REEs: Lanthanum, Cerium, Praseodymium, Neodymium, Samarium
2. Heavy REEs: Europium, Gadolinium, Terbium, Dysprosium, Yttrium
3. Special forms: NdPr (code='NdPr', formula for mixed oxide)

All assigned to rare_earth_chain cluster per section 4. Include:
- IUPAC symbols (La, Ce, Pr, Nd, etc.)
- default_unit='kg', default_basis='$/kg' for separated oxides
- Notes on typical oxide vs metal trading"

## Prompt 9: Add ferroalloys and specialty metals

"Complete metals.yaml with ferroalloys and specialty metals per sections 2, 4, and 13 of METALS_ONTOLOGY_PLAN.md:
1. Ferroalloys with proper basis from section 9's examples:
   - Ferrochrome (FeCr): basis='$/lb Cr contained'
   - Ferromanganese, Ferrovanadium, Ferrotungsten, Ferromolybdenum
2. Specialty metals:
   - Tungsten metal
   - APT (follow exact example from section 2: formula, code='WO3', basis='$/mtu WO3')
   - Tantalum, Niobium, Vanadium

Assign to ferroalloy_chain or sn_ta_nb_w_chain clusters per section 4."

## Prompt 10: Create text extraction module

"Implement metalextractor.py following section 8 of METALS_ONTOLOGY_PLAN.md:
Create extract_metals_from_text() that detects:
1. Element symbols and combinations (Pt/Pd, Ni-Co)
2. Trade specifications (APT 88.5%, P1020, SHG)
3. Chemical forms (lithium carbonate, ferro-chrome)

Return format: [{query:'pt', span:(...), hint:'symbol'}, ...]

Use patterns that feed into metal_identifier() with appropriate category/cluster hints."

## Prompt 11: Write comprehensive tests

"Create tests/test_metals.py with all test cases from section 12 of METALS_ONTOLOGY_PLAN.md:
1. test_symbol_exact() — Pt → Platinum
2. test_aliases() — wolfram → tungsten
3. test_trade_terms() — APT 88.5% → APT with basis='$/mtu WO3'
4. test_colon_hints() — lithium:carbonate → lithium carbonate
5. test_cluster_filtering() — resolve within pgm_complex
6. test_unit_basis_validation() — verify section 9's examples
7. test_text_extraction() — patterns from section 8
8. test_topk_matching() — scored candidates

Each test should verify behavior specified in METALS_ONTOLOGY_PLAN.md."

## Prompt 12: Add integration and documentation

"Complete the integration following sections 1 and 14 of METALS_ONTOLOGY_PLAN.md:
1. Update entityidentity/__init__.py to export metals module
2. Create metals/README.md with usage examples from section 5's API
3. Add example notebook demonstrating all API functions
4. Create CLI tool for testing metal resolution
5. Add GitHub Actions workflow for YAML validation and parquet building
6. Document all source citations from section 10 (IUPAC, USGS, Fastmarkets, WCO)

Ensure all examples reference the exact function signatures from METALS_ONTOLOGY_PLAN.md."

## Important Notes for All Prompts

- Always reference METALS_ONTOLOGY_PLAN.md as the authoritative specification
- Follow the functional, DataFrame-first patterns from entityidentity/countries/
- Use the exact field names, schemas, and formulas specified in the plan
- Include proper source citations (IUPAC, USGS, Fastmarkets) as shown in section 10
- Validate against the examples provided in the plan (APT, FeCr, etc.)