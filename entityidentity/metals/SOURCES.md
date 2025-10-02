# Data Sources and Citations for Metals Ontology

This document provides comprehensive citations for all data sources used in the metals ontology module, as specified in Section 10 of METALS_ONTOLOGY_PLAN.md.

## Source Priority Hierarchy

Sources are integrated with deterministic priority to ensure consistent resolution:

| Priority | Source | Authority | Usage |
|----------|--------|-----------|-------|
| 1 | IUPAC | International Union of Pure and Applied Chemistry | Element names, symbols, atomic properties |
| 2 | USGS | United States Geological Survey | Supply chains, by-products, geology |
| 3 | WCO-HS | World Customs Organization | HS 2022 trade codes |
| 4 | Fastmarkets | Fastmarkets Ltd (formerly Metal Bulletin) | Price specs, commercial standards |
| 5 | Other | Various industry sources | Supplementary information |

## Primary Sources

### 1. IUPAC (Priority 1)

**International Union of Pure and Applied Chemistry**

- **Website**: https://iupac.org/
- **Periodic Table**: https://iupac.org/what-we-do/periodic-table-of-elements/
- **Authority**: Global authority for chemical nomenclature and standards
- **Data Used**:
  - Element names (English standard)
  - Element symbols (1-2 letter codes)
  - Atomic numbers
  - Element discovery and naming conventions

**Specific References**:
- IUPAC Periodic Table of Elements and Isotopes (IPTEI)
- IUPAC Red Book (Nomenclature of Inorganic Chemistry)
- IUPAC Gold Book (Compendium of Chemical Terminology)

### 2. USGS (Priority 2)

**United States Geological Survey**

- **Website**: https://www.usgs.gov/
- **Mineral Commodity Summaries**: https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries
- **Authority**: US federal agency for earth sciences
- **Data Used**:
  - Supply chain relationships
  - By-product and co-product associations
  - Deposit models and geological occurrence
  - Production statistics and reserves

**Specific Publications**:
- USGS Mineral Commodity Summaries 2024
- USGS Professional Paper 1802: Critical Mineral Resources
- USGS Fact Sheets on individual commodities
- USGS Data Series reports on metal production

**Key Supply Chain Relationships from USGS**:
- Rhenium from molybdenum roasting (porphyry copper)
- Selenium/Tellurium from copper anode slimes
- Indium from zinc processing residues
- Gallium from aluminum production (Bayer process)
- Hafnium separated from zirconium
- PGMs from Bushveld Complex and Ni-Cu deposits

### 3. WCO-HS (Priority 3)

**World Customs Organization - Harmonized System**

- **Website**: http://www.wcoomd.org/
- **HS Database**: HS 2022 Edition
- **Authority**: International trade classification standard
- **Data Used**:
  - 6-digit HS codes for metals and metal products
  - Trade nomenclature and descriptions
  - Classification of ores, concentrates, and refined products

**Relevant HS Chapters**:
- Chapter 26: Ores, slag and ash
- Chapter 28: Inorganic chemicals (metal compounds)
- Chapter 71: Precious metals
- Chapter 72-83: Base metals and articles thereof
- Chapter 81: Other base metals (specialty metals)

### 4. Fastmarkets (Priority 4)

**Fastmarkets Ltd**

- **Website**: https://www.fastmarkets.com/
- **Price Specifications**: https://www.fastmarkets.com/methodology
- **Authority**: Leading price reporting agency for metals
- **Data Used**:
  - Price Reference Assessment (PRA) codes
  - Market standard units (mt, lb, kg, toz, mtu)
  - Pricing basis specifications (contained metal, oxide, etc.)
  - Commercial grade specifications

**PRA Code Examples Used**:
- MB-LI-0029: Lithium carbonate 99.5% Li2CO3 min, battery grade
- MB-CO-0005: Cobalt standard grade, in-warehouse Rotterdam
- MB-CO-0017: Cobalt sulfate 20.5% Co min, ex-works China
- MB-NI-0001: Nickel briquettes, min 99.8%, in-warehouse Rotterdam
- MB-NI-0246: Nickel sulfate min 22% Ni, ex-works China
- MB-W-0001: Tungsten APT 88.5% WO3 min, in-warehouse Rotterdam
- MB-V-0001: Ferrovanadium 78% V min, in-warehouse Rotterdam
- MB-V-0002: Vanadium pentoxide 98% V2O5 min, in-warehouse Rotterdam
- MB-TA-0001: Tantalum pentoxide 99.5% Ta2O5 min
- MB-FEM-0001: Ferromanganese high carbon 78% Mn
- MB-FEO-0001: Ferromolybdenum 65-70% Mo
- MB-GRA-0014: Natural flake graphite, -100 mesh, 94-97% C
- MB-GRA-0021: Synthetic graphite, 99.95% C min

## Secondary Sources

### Industry Organizations

**London Metal Exchange (LME)**
- Base metals specifications and contracts
- Standard lot sizes and delivery terms

**Minor Metals Trade Association (MMTA)**
- Specialty metals trading standards
- Industry terminology and practices

**International Precious Metals Institute (IPMI)**
- Precious metals standards and specifications
- Refining and assay standards

### Academic and Technical References

**Mineralogical Databases**:
- Mindat.org - Mineral and locality database
- Webmineral.com - Crystallography and mineral data
- RRUFF Database - Raman spectra of minerals

**Chemical Databases**:
- PubChem - Chemical compound database
- ChemSpider - Chemical structure database
- CAS Registry - Chemical Abstracts Service

## Data Integration Methodology

### Source Priority Rules

1. **Element Data**: IUPAC takes absolute precedence for element names and symbols
2. **Supply Chains**: USGS data preferred for geological and production relationships
3. **Trade Classification**: WCO-HS for international trade codes
4. **Market Standards**: Fastmarkets for commercial specifications and pricing units

### Conflict Resolution

When sources conflict:
- Higher priority source data is retained
- Lower priority data marked in notes field
- Source attribution maintained for transparency

### Version Control

- IUPAC: Using 2024 standard periodic table
- USGS: Mineral Commodity Summaries 2024
- WCO-HS: HS 2022 nomenclature (latest revision)
- Fastmarkets: Current price specifications as of 2024

## Citation Format

Each metal entry in metals.yaml includes source attribution in the format:

```yaml
sources: ["IUPAC", "USGS"]  # Listed in order of data contribution
```

## Updates and Maintenance

- Annual review against USGS Mineral Commodity Summaries
- Quarterly review of Fastmarkets specification changes
- HS code updates every 5 years (next: 2027)
- IUPAC updates as new elements are officially named

## Contact and Corrections

For corrections or additional source suggestions, please submit a GitHub issue with:
- Specific metal or data point in question
- Authoritative source reference
- Suggested correction with justification

## License and Attribution

This compilation integrates public domain data (USGS, IUPAC public data) and referenced commercial standards (Fastmarkets specifications used under fair use for standardization purposes). Users should verify current specifications with original sources for commercial applications.

---

*Last updated: 2024*
*Maintainer: entityidentity project*