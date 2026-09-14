# Nighthawk species codes, families, and eBird import guidance

This reference matches all **130 codes** in Nighthawk's `species.txt` to names and families. The table uses eBird taxonomy **2025**, the latest version returned by eBird on **September 11, 2026**. It includes **128 species and two slash taxa** across **18 families**. Nighthawk's separate `families.txt` contains **19 labels**, including Corvidae, which has no species in this particular species list.

This is a reference for reviewing detections and preparing exports. NFC Tools can now generate untested eBird import files after scheduled recording analysis or bulk analysis, but it does not submit checklists or confirm an analyzer identification.

## Sources and reproducibility

- Nighthawk by Benjamin M. Van Doren and contributors, pinned commit [`0f3dd63`](https://github.com/bmvandoren/Nighthawk/tree/0f3dd635c21bf48cd4c7729ef0a33cb8f5f27aab): [species codes](https://github.com/bmvandoren/Nighthawk/blob/0f3dd635c21bf48cd4c7729ef0a33cb8f5f27aab/nighthawk/taxonomy/species.txt), [family labels](https://github.com/bmvandoren/Nighthawk/blob/0f3dd635c21bf48cd4c7729ef0a33cb8f5f27aab/nighthawk/taxonomy/families.txt), and [bundled taxonomy](https://github.com/bmvandoren/Nighthawk/blob/0f3dd635c21bf48cd4c7729ef0a33cb8f5f27aab/nighthawk/taxonomy/ebird_taxonomy.csv). Its internal taxonomy marker is `select_v6`; this is not an eBird annual taxonomy version. Upstream [license](https://github.com/bmvandoren/Nighthawk/blob/0f3dd635c21bf48cd4c7729ef0a33cb8f5f27aab/LICENSE): CC BY-NC 4.0.
- Cornell Lab of Ornithology: [eBird taxonomy API](https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json) and [available versions](https://api.ebird.org/v2/ref/taxonomy/versions), retrieved September 11, 2026. The full mapping was checked against this API response; individual species pages were spot-checked, not all crawled.
- Match Nighthawk labels to `speciesCode` exactly; take `comName`, `sciName`, `category`, `familySciName`, and `familyComName` from the eBird response. Preserve spelling and numerical suffixes. Codes such as `ovenbi1` are not six-letter banding codes.
- When refreshing this reference, recheck missing codes, changes in taxon category or scope, and the family mappings below. A surviving code does not necessarily retain its former species-level meaning.

## eBird upload format

[eBird's import guide](https://support.ebird.org/en/support/solutions/articles/48000907878) specifies CSV with the template's exact column order. The eBird Record Format sample uses accepted common names in `Common Name` and leaves `Genus` and `Species` blank, so generated upload rows should do the same. These formats do not provide a separate family column. Keep lookup codes and family metadata out of additional upload columns.

- **Record Format:** one observation per row; remove the header row before uploading. A single Record Format file can contain multiple checklists; eBird groups rows into checklists using the repeated location, date, start time, duration, protocol, and effort fields.
- **NFC Tools output:** per-session `ebird_record_import_yyyy-mm-dd_hh-mm.csv` files support hour-by-hour troubleshooting, while `ebird_record_import_night_yyyy-mm-dd.csv` combines the same upload rows for a one-file night import.
- **Encoding:** write upload CSVs as UTF-8 without a byte-order mark so the first common name begins at the first byte.
- **Checklist Format:** checklist effort occupies rows 1–14; taxa start at row 15, with common names in A, scientific names in B, and checklists from C onward. Leave A1 empty and B blank if scientific names are omitted.
- Files must use comma delimiters and be at most 1 MB. Use `MM/DD/YYYY`, supported start-time formats, duration in minutes, and `Y`/`N` for completeness. Include the required location and protocol/effort fields. Consult the linked template for the complete field layout.
- Review unresolved names in the import tool's **Fix Species** stage. This document is not itself an upload template.

## Family-only identifications

A species' family is metadata; a detection identified only to a family is a separate, uncertain identification. For the latter, select an accepted eBird **spuh** (broad identification) with appropriate scope, rather than supplying a bare family label as a species or inventing a name. eBird also supports **slash** taxa for specified alternatives. See [eBird's taxonomy guidance](https://support.ebird.org/en/support/solutions/articles/48000837816-the-ebird-taxonomy).

The following table covers every Nighthawk family label. Names are exact values from the retrieved eBird taxonomy. “Review required” means no family-wide equivalent was established here; narrower genus or species-pair entries must not be chosen solely from the family label. If review cannot refine the identification, choose an appropriate broader accepted taxon or retain the record for review. Do not silently discard it or assign a species.

| Nighthawk family | eBird code | Common name | Scientific name | Mapping scope |
| --- | --- | --- | --- | --- |
| Turdidae | [thrush1](https://ebird.org/species/thrush1) | thrush sp. | Turdidae sp. | Family-wide scientific-name match. |
| Parulidae | [warble](https://ebird.org/species/warble) | new world warbler sp. | Parulidae sp. | Family-wide scientific-name match. |
| Passerellidae | [sparro1](https://ebird.org/species/sparro1) | new world sparrow sp. | Passerellidae sp. | Family-wide scientific-name match. |
| Cardinalidae | — | Review required | — | Genus entries such as Passerina sp. cover only part of this family. |
| Ardeidae | [heron1](https://ebird.org/species/heron1) | heron sp. | Ardeidae sp. | Family-wide scientific-name match. |
| Charadriidae | [plover2](https://ebird.org/species/plover2) | plover sp. | Charadriidae sp. | Family-wide scientific-name match. |
| Regulidae | — | Review required | — | Do not infer Golden-crowned Kinglet from a family label. |
| Scolopacidae | [scolop1](https://ebird.org/species/scolop1) | Scolopacidae sp. | Scolopacidae sp. | Family-wide scientific-name match. |
| Icteridae | [blackb](https://ebird.org/species/blackb) | blackbird sp. | Icteridae sp. | Family-wide scientific-name match. |
| Cuculidae | [cuckoo3](https://ebird.org/species/cuckoo3) | cuckoo sp. (Cuculidae sp.) | Cuculidae sp. | Family-wide scientific-name match. |
| Motacillidae | — | Review required | — | Pipit sp. excludes wagtails and longclaws. |
| Calcariidae | — | Review required | — | Longspur sp. excludes snow buntings. |
| Sittidae | [nuthat1](https://ebird.org/species/nuthat1) | nuthatch sp. | Sitta sp. | Single-genus family in this taxonomy. |
| Laridae | [y00728](https://ebird.org/species/y00728) | gull/tern sp. | Laridae sp. | Scientific name matches the family; retain this exact accepted label. |
| Corvidae | [corvid2](https://ebird.org/species/corvid2) | corvid sp. | Corvidae sp. | Family-wide scientific-name match. |
| Recurvirostridae | [y00722](https://ebird.org/species/y00722) | stilt/avocet sp. | Recurvirostridae sp. | Family-wide scientific-name match. |
| Alaudidae | [lark1](https://ebird.org/species/lark1) | lark sp. | Alaudidae sp. | Family-wide scientific-name match. |
| Bombycillidae | — | Review required | — | Do not infer Cedar Waxwing from a family label. |
| Haematopodidae | [oyster1](https://ebird.org/species/oyster1) | oystercatcher sp. | Haematopus sp. | Single-genus family in this taxonomy. |

Do not add a family total as another observation alongside the same birds identified to species. Preserve the identification level supported by review. Nighthawk acoustic groups and order labels require their own scope review; this family table does not map them.

## Order-level labels

Nighthawk can also emit labels above the family level. Keep these separate from the family table and use them only when no narrower identification is available.

| Nighthawk label | eBird common name | Scientific name | Mapping scope |
| --- | --- | --- | --- |
| Charadriiformes | shorebird sp. | Charadriiformes sp. | Practical NFC upload bucket for broad shorebird-type calls; narrower Charadriidae, Scolopacidae, and Laridae mappings should be used when available. |
| Cuculiformes | cuckoo sp. (Cuculidae sp.) | Cuculidae sp. | Practical NFC upload bucket for broad cuckoo-type calls; narrower species or Cuculidae mappings should be used when available. |

## NFC counts and checklist metadata

For the [NFC protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC), put call totals in species comments as `NFC 187`, for example; do not equate detection rows or calls with individual birds. Mark completeness `N`. Split checklists at midnight and keep civil-to-astronomical twilight observations separate from the astronomical-night count. eBird recommends sessions under an hour and a dedicated remote-listening account for recordings reviewed later. Use the appropriate specialized protocol code from the import documentation.

### Civil twilight checklist comments

For future checklist exports, add the following exact text to **checklist-level comments**, alongside any existing comments:

| Boundary | Checklist ending at the boundary | Checklist starting at the boundary |
| --- | --- | --- |
| Evening civil twilight (civil dusk) | `Ending at civil twilight` | `Starting at civil twilight` |
| Morning civil twilight (civil dawn) | `Ending at civil twilight` | `Starting at civil twilight` |

Apply each comment only when the checklist's corresponding endpoint is at that civil boundary. Do not infer it from a `civil_evening` or `civil_morning` segment label, from a detection time, or from an astronomical twilight boundary. A checklist entirely within a twilight period gets neither comment. If a checklist starts at one civil boundary and ends at another, include both comments, starting first. Add each phrase once and preserve other checklist comments.

Present each phrase as its own line in a checklist comment editor or preview. For eBird CSV import, combine comment data points with ` | ` in the single checklist-comments field, because the [import guide](https://support.ebird.org/en/support/solutions/articles/48000907878) prohibits embedded line breaks. The current exporter keeps weather conditions in checklist comments, removes date/time text from comments, and leaves manual species and location matching to eBird.

## Changes from the bundled Nighthawk taxonomy

Five codes have changed common names, scientific names, or taxon scope. The two slash mappings preserve uncertainty after splits; choose an individual successor species only when independently justified by the observation.

| Code | Bundled common name | Bundled scientific name | Current common name | Current scientific name | Current category |
| --- | --- | --- | --- | --- | --- |
| `bcnher` | Black-crowned Night-Heron | Nycticorax nycticorax | Black-crowned Night Heron | Nycticorax nycticorax | species |
| `leabit` | Least Bittern | Ixobrychus exilis | Least Bittern | Botaurus exilis | species |
| `whimbr` | Whimbrel | Numenius phaeopus | Hudsonian/Eurasian Whimbrel | Numenius hudsonicus/phaeopus | slash |
| `ycnher` | Yellow-crowned Night-Heron | Nyctanassa violacea | Yellow-crowned Night Heron | Nyctanassa violacea | species |
| `yelwar` | Yellow Warbler | Setophaga petechia | Northern/Mangrove Yellow Warbler | Setophaga aestiva/petechia | slash |

## Species and family lookup

The first 130 rows retain Nighthawk’s species-code order. These are current eBird names for the exact source codes; consult the changes above when interpreting older model labels.

The final 19 rows define family usage. Their **eBird code** and **Species** cells are `n/a`, as these are family reference rows. The **Family** cell pairs the Nighthawk family with eBird’s accepted broad-identification name, such as `Ardeidae — heron sp.`. Accepted entries have category `spuh`; unresolved entries say `Review required`. The detailed [family mapping table](#family-only-identifications) above retains the actual eBird taxon codes and scope notes. `n/a` here does not mean that accepted family-level entries lack eBird codes.

| eBird code | Species | Scientific name | Family | Category |
| --- | --- | --- | --- | --- |
| [amered](https://ebird.org/species/amered) | American Redstart | Setophaga ruticilla | Parulidae (New World Warblers) | species |
| [amtspa](https://ebird.org/species/amtspa) | American Tree Sparrow | Spizelloides arborea | Passerellidae (New World Sparrows) | species |
| [bawwar](https://ebird.org/species/bawwar) | Black-and-white Warbler | Mniotilta varia | Parulidae (New World Warblers) | species |
| [btbwar](https://ebird.org/species/btbwar) | Black-throated Blue Warbler | Setophaga caerulescens | Parulidae (New World Warblers) | species |
| [camwar](https://ebird.org/species/camwar) | Cape May Warbler | Setophaga tigrina | Parulidae (New World Warblers) | species |
| [chispa](https://ebird.org/species/chispa) | Chipping Sparrow | Spizella passerina | Passerellidae (New World Sparrows) | species |
| [chswar](https://ebird.org/species/chswar) | Chestnut-sided Warbler | Setophaga pensylvanica | Parulidae (New World Warblers) | species |
| [comyel](https://ebird.org/species/comyel) | Common Yellowthroat | Geothlypis trichas | Parulidae (New World Warblers) | species |
| [daejun](https://ebird.org/species/daejun) | Dark-eyed Junco | Junco hyemalis | Passerellidae (New World Sparrows) | species |
| [gycthr](https://ebird.org/species/gycthr) | Gray-cheeked Thrush | Catharus minimus | Turdidae (Thrushes and Allies) | species |
| [herthr](https://ebird.org/species/herthr) | Hermit Thrush | Catharus guttatus | Turdidae (Thrushes and Allies) | species |
| [norpar](https://ebird.org/species/norpar) | Northern Parula | Setophaga americana | Parulidae (New World Warblers) | species |
| [ovenbi1](https://ebird.org/species/ovenbi1) | Ovenbird | Seiurus aurocapilla | Parulidae (New World Warblers) | species |
| [robgro](https://ebird.org/species/robgro) | Rose-breasted Grosbeak | Pheucticus ludovicianus | Cardinalidae (Cardinals and Allies) | species |
| [savspa](https://ebird.org/species/savspa) | Savannah Sparrow | Passerculus sandwichensis | Passerellidae (New World Sparrows) | species |
| [swathr](https://ebird.org/species/swathr) | Swainson's Thrush | Catharus ustulatus | Turdidae (Thrushes and Allies) | species |
| [veery](https://ebird.org/species/veery) | Veery | Catharus fuscescens | Turdidae (Thrushes and Allies) | species |
| [whtspa](https://ebird.org/species/whtspa) | White-throated Sparrow | Zonotrichia albicollis | Passerellidae (New World Sparrows) | species |
| [woothr](https://ebird.org/species/woothr) | Wood Thrush | Hylocichla mustelina | Turdidae (Thrushes and Allies) | species |
| [whcspa](https://ebird.org/species/whcspa) | White-crowned Sparrow | Zonotrichia leucophrys | Passerellidae (New World Sparrows) | species |
| [canwar](https://ebird.org/species/canwar) | Canada Warbler | Cardellina canadensis | Parulidae (New World Warblers) | species |
| [graspa](https://ebird.org/species/graspa) | Grasshopper Sparrow | Ammodramus savannarum | Passerellidae (New World Sparrows) | species |
| [indbun](https://ebird.org/species/indbun) | Indigo Bunting | Passerina cyanea | Cardinalidae (Cardinals and Allies) | species |
| [wlswar](https://ebird.org/species/wlswar) | Wilson's Warbler | Cardellina pusilla | Parulidae (New World Warblers) | species |
| [boboli](https://ebird.org/species/boboli) | Bobolink | Dolichonyx oryzivorus | Icteridae (Troupials and Allies) | species |
| [norwat](https://ebird.org/species/norwat) | Northern Waterthrush | Parkesia noveboracensis | Parulidae (New World Warblers) | species |
| [palwar](https://ebird.org/species/palwar) | Palm Warbler | Setophaga palmarum | Parulidae (New World Warblers) | species |
| [mouwar](https://ebird.org/species/mouwar) | Mourning Warbler | Geothlypis philadelphia | Parulidae (New World Warblers) | species |
| [yerwar](https://ebird.org/species/yerwar) | Yellow-rumped Warbler | Setophaga coronata | Parulidae (New World Warblers) | species |
| [clcspa](https://ebird.org/species/clcspa) | Clay-colored Sparrow | Spizella pallida | Passerellidae (New World Sparrows) | species |
| [hoowar](https://ebird.org/species/hoowar) | Hooded Warbler | Setophaga citrina | Parulidae (New World Warblers) | species |
| [lecspa](https://ebird.org/species/lecspa) | LeConte's Sparrow | Ammospiza leconteii | Passerellidae (New World Sparrows) | species |
| [fiespa](https://ebird.org/species/fiespa) | Field Sparrow | Spizella pusilla | Passerellidae (New World Sparrows) | species |
| [scatan](https://ebird.org/species/scatan) | Scarlet Tanager | Piranga olivacea | Cardinalidae (Cardinals and Allies) | species |
| [yebcuc](https://ebird.org/species/yebcuc) | Yellow-billed Cuckoo | Coccyzus americanus | Cuculidae (Cuckoos) | species |
| [bkbcuc](https://ebird.org/species/bkbcuc) | Black-billed Cuckoo | Coccyzus erythropthalmus | Cuculidae (Cuckoos) | species |
| [bcnher](https://ebird.org/species/bcnher) | Black-crowned Night Heron | Nycticorax nycticorax | Ardeidae (Herons, Egrets, and Bitterns) | species |
| [vesspa](https://ebird.org/species/vesspa) | Vesper Sparrow | Pooecetes gramineus | Passerellidae (New World Sparrows) | species |
| [leabit](https://ebird.org/species/leabit) | Least Bittern | Botaurus exilis | Ardeidae (Herons, Egrets, and Bitterns) | species |
| [uplsan](https://ebird.org/species/uplsan) | Upland Sandpiper | Bartramia longicauda | Scolopacidae (Sandpipers and Allies) | species |
| [amebit](https://ebird.org/species/amebit) | American Bittern | Botaurus lentiginosus | Ardeidae (Herons, Egrets, and Bitterns) | species |
| [grnher](https://ebird.org/species/grnher) | Green Heron | Butorides virescens | Ardeidae (Herons, Egrets, and Bitterns) | species |
| [macwar](https://ebird.org/species/macwar) | MacGillivray's Warbler | Geothlypis tolmiei | Parulidae (New World Warblers) | species |
| [dickci](https://ebird.org/species/dickci) | Dickcissel | Spiza americana | Cardinalidae (Cardinals and Allies) | species |
| [amepip](https://ebird.org/species/amepip) | American Pipit | Anthus rubescens | Motacillidae (Wagtails and Pipits) | species |
| [amerob](https://ebird.org/species/amerob) | American Robin | Turdus migratorius | Turdidae (Thrushes and Allies) | species |
| [greyel](https://ebird.org/species/greyel) | Greater Yellowlegs | Tringa melanoleuca | Scolopacidae (Sandpipers and Allies) | species |
| [leasan](https://ebird.org/species/leasan) | Least Sandpiper | Calidris minutilla | Scolopacidae (Sandpipers and Allies) | species |
| [semplo](https://ebird.org/species/semplo) | Semipalmated Plover | Charadrius semipalmatus | Charadriidae (Plovers and Lapwings) | species |
| [shbdow](https://ebird.org/species/shbdow) | Short-billed Dowitcher | Limnodromus griseus | Scolopacidae (Sandpipers and Allies) | species |
| [sposan](https://ebird.org/species/sposan) | Spotted Sandpiper | Actitis macularius | Scolopacidae (Sandpipers and Allies) | species |
| [solsan](https://ebird.org/species/solsan) | Solitary Sandpiper | Tringa solitaria | Scolopacidae (Sandpipers and Allies) | species |
| [laplon](https://ebird.org/species/laplon) | Lapland Longspur | Calcarius lapponicus | Calcariidae (Longspurs and Snow Buntings) | species |
| [rebnut](https://ebird.org/species/rebnut) | Red-breasted Nuthatch | Sitta canadensis | Sittidae (Nuthatches) | species |
| [babwar](https://ebird.org/species/babwar) | Bay-breasted Warbler | Setophaga castanea | Parulidae (New World Warblers) | species |
| [bkpwar](https://ebird.org/species/bkpwar) | Blackpoll Warbler | Setophaga striata | Parulidae (New World Warblers) | species |
| [btnwar](https://ebird.org/species/btnwar) | Black-throated Green Warbler | Setophaga virens | Parulidae (New World Warblers) | species |
| [magwar](https://ebird.org/species/magwar) | Magnolia Warbler | Setophaga magnolia | Parulidae (New World Warblers) | species |
| [naswar](https://ebird.org/species/naswar) | Nashville Warbler | Leiothlypis ruficapilla | Parulidae (New World Warblers) | species |
| [tenwar](https://ebird.org/species/tenwar) | Tennessee Warbler | Leiothlypis peregrina | Parulidae (New World Warblers) | species |
| [balori](https://ebird.org/species/balori) | Baltimore Oriole | Icterus galbula | Icteridae (Troupials and Allies) | species |
| [bicthr](https://ebird.org/species/bicthr) | Bicknell's Thrush | Catharus bicknelli | Turdidae (Thrushes and Allies) | species |
| [bkbplo](https://ebird.org/species/bkbplo) | Black-bellied Plover | Pluvialis squatarola | Charadriidae (Plovers and Lapwings) | species |
| [bkbwar](https://ebird.org/species/bkbwar) | Blackburnian Warbler | Setophaga fusca | Parulidae (New World Warblers) | species |
| [bknsti](https://ebird.org/species/bknsti) | Black-necked Stilt | Himantopus mexicanus | Recurvirostridae (Stilts and Avocets) | species |
| [blkski](https://ebird.org/species/blkski) | Black Skimmer | Rynchops niger | Laridae (Gulls, Terns, and Skimmers) | species |
| [blugrb1](https://ebird.org/species/blugrb1) | Blue Grosbeak | Passerina caerulea | Cardinalidae (Cardinals and Allies) | species |
| [brespa](https://ebird.org/species/brespa) | Brewer's Sparrow | Spizella breweri | Passerellidae (New World Sparrows) | species |
| [btywar](https://ebird.org/species/btywar) | Black-throated Gray Warbler | Setophaga nigrescens | Parulidae (New World Warblers) | species |
| [buwwar](https://ebird.org/species/buwwar) | Blue-winged Warbler | Vermivora cyanoptera | Parulidae (New World Warblers) | species |
| [caster1](https://ebird.org/species/caster1) | Caspian Tern | Hydroprogne caspia | Laridae (Gulls, Terns, and Skimmers) | species |
| [cerwar](https://ebird.org/species/cerwar) | Cerulean Warbler | Setophaga cerulea | Parulidae (New World Warblers) | species |
| [comter](https://ebird.org/species/comter) | Common Tern | Sterna hirundo | Laridae (Gulls, Terns, and Skimmers) | species |
| [conwar](https://ebird.org/species/conwar) | Connecticut Warbler | Oporornis agilis | Parulidae (New World Warblers) | species |
| [easmea](https://ebird.org/species/easmea) | Eastern Meadowlark | Sturnella magna | Icteridae (Troupials and Allies) | species |
| [forter](https://ebird.org/species/forter) | Forster's Tern | Sterna forsteri | Laridae (Gulls, Terns, and Skimmers) | species |
| [foxspa](https://ebird.org/species/foxspa) | Fox Sparrow | Passerella iliaca | Passerellidae (New World Sparrows) | species |
| [gockin](https://ebird.org/species/gockin) | Golden-crowned Kinglet | Regulus satrapa | Regulidae (Kinglets) | species |
| [gocspa](https://ebird.org/species/gocspa) | Golden-crowned Sparrow | Zonotrichia atricapilla | Passerellidae (New World Sparrows) | species |
| [gowwar](https://ebird.org/species/gowwar) | Golden-winged Warbler | Vermivora chrysoptera | Parulidae (New World Warblers) | species |
| [grbher3](https://ebird.org/species/grbher3) | Great Blue Heron | Ardea herodias | Ardeidae (Herons, Egrets, and Bitterns) | species |
| [greegr](https://ebird.org/species/greegr) | Great Egret | Ardea alba | Ardeidae (Herons, Egrets, and Bitterns) | species |
| [henspa](https://ebird.org/species/henspa) | Henslow's Sparrow | Centronyx henslowii | Passerellidae (New World Sparrows) | species |
| [harspa](https://ebird.org/species/harspa) | Harris's Sparrow | Zonotrichia querula | Passerellidae (New World Sparrows) | species |
| [herwar](https://ebird.org/species/herwar) | Hermit Warbler | Setophaga occidentalis | Parulidae (New World Warblers) | species |
| [horlar](https://ebird.org/species/horlar) | Horned Lark | Eremophila alpestris | Alaudidae (Larks) | species |
| [kenwar](https://ebird.org/species/kenwar) | Kentucky Warbler | Geothlypis formosa | Parulidae (New World Warblers) | species |
| [killde](https://ebird.org/species/killde) | Killdeer | Charadrius vociferus | Charadriidae (Plovers and Lapwings) | species |
| [kirwar](https://ebird.org/species/kirwar) | Kirtland's Warbler | Setophaga kirtlandii | Parulidae (New World Warblers) | species |
| [lazbun](https://ebird.org/species/lazbun) | Lazuli Bunting | Passerina amoena | Cardinalidae (Cardinals and Allies) | species |
| [larspa](https://ebird.org/species/larspa) | Lark Sparrow | Chondestes grammacus | Passerellidae (New World Sparrows) | species |
| [lesyel](https://ebird.org/species/lesyel) | Lesser Yellowlegs | Tringa flavipes | Scolopacidae (Sandpipers and Allies) | species |
| [linspa](https://ebird.org/species/linspa) | Lincoln's Sparrow | Melospiza lincolnii | Passerellidae (New World Sparrows) | species |
| [lobcur](https://ebird.org/species/lobcur) | Long-billed Curlew | Numenius americanus | Scolopacidae (Sandpipers and Allies) | species |
| [lobdow](https://ebird.org/species/lobdow) | Long-billed Dowitcher | Limnodromus scolopaceus | Scolopacidae (Sandpipers and Allies) | species |
| [nstspa](https://ebird.org/species/nstspa) | Nelson's Sparrow | Ammospiza nelsoni | Passerellidae (New World Sparrows) | species |
| [orcori](https://ebird.org/species/orcori) | Orchard Oriole | Icterus spurius | Icteridae (Troupials and Allies) | species |
| [orcwar](https://ebird.org/species/orcwar) | Orange-crowned Warbler | Leiothlypis celata | Parulidae (New World Warblers) | species |
| [paibun](https://ebird.org/species/paibun) | Painted Bunting | Passerina ciris | Cardinalidae (Cardinals and Allies) | species |
| [pinwar](https://ebird.org/species/pinwar) | Pine Warbler | Setophaga pinus | Parulidae (New World Warblers) | species |
| [prawar](https://ebird.org/species/prawar) | Prairie Warbler | Setophaga discolor | Parulidae (New World Warblers) | species |
| [prowar](https://ebird.org/species/prowar) | Prothonotary Warbler | Protonotaria citrea | Parulidae (New World Warblers) | species |
| [sander](https://ebird.org/species/sander) | Sanderling | Calidris alba | Scolopacidae (Sandpipers and Allies) | species |
| [seaspa](https://ebird.org/species/seaspa) | Seaside Sparrow | Ammospiza maritima | Passerellidae (New World Sparrows) | species |
| [smilon](https://ebird.org/species/smilon) | Smith's Longspur | Calcarius pictus | Calcariidae (Longspurs and Snow Buntings) | species |
| [snobun](https://ebird.org/species/snobun) | Snow Bunting | Plectrophenax nivalis | Calcariidae (Longspurs and Snow Buntings) | species |
| [sonspa](https://ebird.org/species/sonspa) | Song Sparrow | Melospiza melodia | Passerellidae (New World Sparrows) | species |
| [sprpip](https://ebird.org/species/sprpip) | Sprague's Pipit | Anthus spragueii | Motacillidae (Wagtails and Pipits) | species |
| [sumtan](https://ebird.org/species/sumtan) | Summer Tanager | Piranga rubra | Cardinalidae (Cardinals and Allies) | species |
| [swawar](https://ebird.org/species/swawar) | Swainson's Warbler | Limnothlypis swainsonii | Parulidae (New World Warblers) | species |
| [towwar](https://ebird.org/species/towwar) | Townsend's Warbler | Setophaga townsendi | Parulidae (New World Warblers) | species |
| [wesmea](https://ebird.org/species/wesmea) | Western Meadowlark | Sturnella neglecta | Icteridae (Troupials and Allies) | species |
| [whimbr](https://ebird.org/species/whimbr) | Hudsonian/Eurasian Whimbrel | Numenius hudsonicus/phaeopus | Scolopacidae (Sandpipers and Allies) | slash |
| [willet1](https://ebird.org/species/willet1) | Willet | Tringa semipalmata | Scolopacidae (Sandpipers and Allies) | species |
| [wilsni1](https://ebird.org/species/wilsni1) | Wilson's Snipe | Gallinago delicata | Scolopacidae (Sandpipers and Allies) | species |
| [woewar1](https://ebird.org/species/woewar1) | Worm-eating Warbler | Helmitheros vermivorum | Parulidae (New World Warblers) | species |
| [ycnher](https://ebird.org/species/ycnher) | Yellow-crowned Night Heron | Nyctanassa violacea | Ardeidae (Herons, Egrets, and Bitterns) | species |
| [yelwar](https://ebird.org/species/yelwar) | Northern/Mangrove Yellow Warbler | Setophaga aestiva/petechia | Parulidae (New World Warblers) | slash |
| [yetwar](https://ebird.org/species/yetwar) | Yellow-throated Warbler | Setophaga dominica | Parulidae (New World Warblers) | species |
| [swaspa](https://ebird.org/species/swaspa) | Swamp Sparrow | Melospiza georgiana | Passerellidae (New World Sparrows) | species |
| [virwar](https://ebird.org/species/virwar) | Virginia's Warbler | Leiothlypis virginiae | Parulidae (New World Warblers) | species |
| [triher](https://ebird.org/species/triher) | Tricolored Heron | Egretta tricolor | Ardeidae (Herons, Egrets, and Bitterns) | species |
| [grawar](https://ebird.org/species/grawar) | Grace's Warbler | Setophaga graciae | Parulidae (New World Warblers) | species |
| [cedwax](https://ebird.org/species/cedwax) | Cedar Waxwing | Bombycilla cedrorum | Bombycillidae (Waxwings) | species |
| [amgplo](https://ebird.org/species/amgplo) | American Golden-Plover | Pluvialis dominica | Charadriidae (Plovers and Lapwings) | species |
| [ameavo](https://ebird.org/species/ameavo) | American Avocet | Recurvirostra americana | Recurvirostridae (Stilts and Avocets) | species |
| [ameoys](https://ebird.org/species/ameoys) | American Oystercatcher | Haematopus palliatus | Haematopodidae (Oystercatchers) | species |
| [baisan](https://ebird.org/species/baisan) | Baird's Sandpiper | Calidris bairdii | Scolopacidae (Sandpipers and Allies) | species |
| [blkoys](https://ebird.org/species/blkoys) | Black Oystercatcher | Haematopus bachmani | Haematopodidae (Oystercatchers) | species |
| [dunlin](https://ebird.org/species/dunlin) | Dunlin | Calidris alpina | Scolopacidae (Sandpipers and Allies) | species |
| n/a | n/a | Turdidae sp. | Turdidae — thrush sp. | spuh |
| n/a | n/a | Parulidae sp. | Parulidae — new world warbler sp. | spuh |
| n/a | n/a | Passerellidae sp. | Passerellidae — new world sparrow sp. | spuh |
| n/a | n/a | n/a | Cardinalidae — Review required | n/a |
| n/a | n/a | Ardeidae sp. | Ardeidae — heron sp. | spuh |
| n/a | n/a | Charadriidae sp. | Charadriidae — plover sp. | spuh |
| n/a | n/a | n/a | Regulidae — Review required | n/a |
| n/a | n/a | Scolopacidae sp. | Scolopacidae — Scolopacidae sp. | spuh |
| n/a | n/a | Icteridae sp. | Icteridae — blackbird sp. | spuh |
| n/a | n/a | Cuculidae sp. | Cuculidae — cuckoo sp. (Cuculidae sp.) | spuh |
| n/a | n/a | n/a | Motacillidae — Review required | n/a |
| n/a | n/a | n/a | Calcariidae — Review required | n/a |
| n/a | n/a | Sitta sp. | Sittidae — nuthatch sp. | spuh |
| n/a | n/a | Laridae sp. | Laridae — gull/tern sp. | spuh |
| n/a | n/a | Corvidae sp. | Corvidae — corvid sp. | spuh |
| n/a | n/a | Recurvirostridae sp. | Recurvirostridae — stilt/avocet sp. | spuh |
| n/a | n/a | Alaudidae sp. | Alaudidae — lark sp. | spuh |
| n/a | n/a | n/a | Bombycillidae — Review required | n/a |
| n/a | n/a | Haematopus sp. | Haematopodidae — oystercatcher sp. | spuh |
