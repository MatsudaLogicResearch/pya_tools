# CHANGELOG

このファイルは UTF-8 で記述されています。

---

## [0.1.7] 2025-10-29
### Modified
- pya_gds2lef
 - Change layer from BOTTOM to TOP in in_json_tech.

## [0.1.6] 2025-10-28
### Modified
- pya_gds2lef
 - Support Text or Pin Polygon as PinText.

## [0.1.5] 2025-10-27
### Modified
- pya_gds2lef
 - Support Text or Pin Polygon as PinText.

## [0.1.4] 2025-10-17
### Modified
- pya_gds2lef
 - Added timestamp comment to the top of the LEF file for traceability.

## [0.1.3] 2025-10-16
### Modified
- pya_gds2lef
  - Set FOREIGN position in LEF based on the BOUNDARY in GDS.

## [0.1.2] 2025-10-16
### Modified
- pya_gds2lef
  - Changed GDS layer name for ANTENNAAREA from GATE/DIFF to GATEAREA/DIFFAREA in `in_jsonc_gdslayer`.
  - Limited TEXT layer search to depth=0(top cell only), searched only once.

## [0.1.1] 2025-10-15
### Added
- runner
- pya_gds2lef
- pya_flatspice
