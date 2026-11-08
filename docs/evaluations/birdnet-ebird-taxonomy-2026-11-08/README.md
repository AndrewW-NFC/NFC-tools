# BirdNET → eBird taxonomy audit — 2026-11-08

Compared the installed BirdNET 3 acoustic model's generated English (en_us) labels against the live eBird v2026 taxonomy, retrieved November 8, 2026. eBird's taxonomy versions endpoint confirmed 2026 as latest. This audits possible model outputs worldwide, not just detections in a particular recording.

Sources: [eBird taxonomy API](https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=csv&locale=en), [eBird versions](https://api.ebird.org/v2/ref/taxonomy/versions), and the locally cached BirdNET acoustic labels plus taxonomy v0.2-Jun2026. Input paths and SHA-256 hashes are recorded in audit.json.

This is the original audit snapshot. The export implementation now uses its results through the [versioned crosswalk](../../reference/birdnet-ebird-crosswalk.md); see that guide for current behavior and maintenance.

## Results

| Classification | Labels |
| --- | ---: |
| exact | 8,087 |
| unresolved | 176 |
| other_common_name_change | 714 |
| non_bird | 1,726 |
| punctuation_spacing | 729 |
| common_name_only_review | 58 |
| capitalization | 31 |
| cached_species_code_review | 39 |

There are 9,834 bird labels and 1,726 non-bird labels. Among birds, 8,087 match both names exactly; 1,474 have an exact scientific-name match but a differing common name. Another 97 have candidate matches using a cached species code or common name only, and 176 remain unresolved under these rules.

## Interpretation

The current export constructs `Taxon(common, scientific)` directly from BirdNET CSV rows (`src/nfc_tools/ebird_export.py`); it does not canonicalize BirdNET names to eBird. These are name differences, not experimentally verified eBird import rejections. Scientific-name equality supports reconciliation but does not by itself prove identical taxonomic scope across versions.

Punctuation/spacing means the names become identical after removing non-word characters and ignoring case. Capitalization is counted separately. Other common-name changes include regional spellings (Gray/Grey), alternate names, and renames. The 97 candidate matches are explicitly review-only: genus changes, splits, lumps, and subspecies can require taxonomic judgment. Unresolved means this audit found no unique match, not that eBird necessarily lacks the bird. No fuzzy matches were accepted.

Recommended export approach: use a versioned eBird crosswalk to emit its canonical names; retain original BirdNET names in review output; flag uncertain taxonomy mappings for review. Do not globally insert/remove hyphens or silently resolve splits and lumps. This audit does not change application behavior.

## Detailed differences and review candidates

### punctuation_spacing

| BirdNET common name | BirdNET scientific name | eBird common name / candidate | eBird scientific name | eBird code |
| --- | --- | --- | --- | --- |
| Seychelles Blue Pigeon | Alectroenas pulcherrimus | Seychelles Blue-Pigeon | Alectroenas pulcherrimus | sebpig1 |
| Papuan King Parrot | Alisterus chloropterus | Papuan King-Parrot | Alisterus chloropterus | pakpar1 |
| Australian King Parrot | Alisterus scapularis | Australian King-Parrot | Alisterus scapularis | aukpar1 |
| Lesser Ground Robin | Amalocichla incerta | Lesser Ground-Robin | Amalocichla incerta | legrob1 |
| Greater Ground Robin | Amalocichla sclateriana | Greater Ground-Robin | Amalocichla sclateriana | grgrob1 |
| Tibetan Sand Plover | Anarhynchus atrifrons | Tibetan Sand-Plover | Anarhynchus atrifrons | lessap1 |
| Greater Sand Plover | Anarhynchus leschenaultii | Greater Sand-Plover | Anarhynchus leschenaultii | grsplo |
| Siberian Sand Plover | Anarhynchus mongolus | Siberian Sand-Plover | Anarhynchus mongolus | lessap2 |
| Hooded Mountain Toucan | Andigena cucullata | Hooded Mountain-Toucan | Andigena cucullata | homtou1 |
| Plate-billed Mountain Toucan | Andigena laminirostris | Plate-billed Mountain-Toucan | Andigena laminirostris | pbmtou1 |
| Black-billed Mountain Toucan | Andigena nigrirostris | Black-billed Mountain-Toucan | Andigena nigrirostris | bbmtou1 |
| Taiga Bean Goose | Anser fabalis | Taiga Bean-Goose | Anser fabalis | taibeg1 |
| Tundra Bean Goose | Anser serrirostris | Tundra Bean-Goose | Anser serrirostris | tunbeg1 |
| Forest Penduline Tit | Anthoscopus flavifrons | Forest Penduline-Tit | Anthoscopus flavifrons | foptit1 |
| Cape Penduline Tit | Anthoscopus minutus | Cape Penduline-Tit | Anthoscopus minutus | soptit1 |
| Mouse-colored Penduline Tit | Anthoscopus musculus | Mouse-colored Penduline-Tit | Anthoscopus musculus | mcptit1 |
| Yellow Penduline Tit | Anthoscopus parvulus | Yellow Penduline-Tit | Anthoscopus parvulus | yeptit1 |
| Sennar Penduline Tit | Anthoscopus punctifrons | Sennar Penduline-Tit | Anthoscopus punctifrons | septit1 |
| Oriental Pied Hornbill | Anthracoceros albirostris | Oriental Pied-Hornbill | Anthracoceros albirostris | orphor1 |
| Malabar Pied Hornbill | Anthracoceros coronatus | Malabar Pied-Hornbill | Anthracoceros coronatus | maphor1 |
| California Scrub Jay | Aphelocoma californica | California Scrub-Jay | Aphelocoma californica | cowscj1 |
| Florida Scrub Jay | Aphelocoma coerulescens | Florida Scrub-Jay | Aphelocoma coerulescens | flsjay |
| Island Scrub Jay | Aphelocoma insularis | Island Scrub-Jay | Aphelocoma insularis | issjay |
| Woodhouse's Scrub Jay | Aphelocoma woodhouseii | Woodhouse's Scrub-Jay | Aphelocoma woodhouseii | wooscj2 |
| Russet-naped Wood Rail | Aramides albiventris | Russet-naped Wood-Rail | Aramides albiventris | runwor1 |
| Rufous-necked Wood Rail | Aramides axillaris | Rufous-necked Wood-Rail | Aramides axillaris | rnwrai1 |
| Little Wood Rail | Aramides mangle | Little Wood-Rail | Aramides mangle | liwrai1 |
| Slaty-breasted Wood Rail | Aramides saracura | Slaty-breasted Wood-Rail | Aramides saracura | sbwrai1 |
| Brown Wood Rail | Aramides wolfi | Brown Wood-Rail | Aramides wolfi | brwrai1 |
| Giant Wood Rail | Aramides ypecaha | Giant Wood-Rail | Aramides ypecaha | giwrai1 |
| Western Cattle Egret | Ardea ibis | Western Cattle-Egret | Ardea ibis | categr1 |
| Chinese Pond Heron | Ardeola bacchus | Chinese Pond-Heron | Ardeola bacchus | chpher1 |
| Indian Pond Heron | Ardeola grayii | Indian Pond-Heron | Ardeola grayii | inpher1 |
| Javan Pond Heron | Ardeola speciosa | Javan Pond-Heron | Ardeola speciosa | japher1 |
| Red-capped Forest Warbler | Artisornis metopias | Red-capped Forest-warbler | Artisornis metopias | afrtai2 |
| Long-billed Forest Warbler | Artisornis moreaui | Long-billed Forest-warbler | Artisornis moreaui | lobtai1 |
| Pale-eyed Pygmy Tyrant | Atalotriccus pilaris | Pale-eyed Pygmy-Tyrant | Atalotriccus pilaris | peptyr1 |
| Rufous-headed Ground Roller | Atelornis crossleyi | Rufous-headed Ground-Roller | Atelornis crossleyi | rhgrol1 |
| Pitta-like Ground Roller | Atelornis pittoides | Pitta-like Ground-Roller | Atelornis pittoides | plgrol1 |
| Noisy Scrubbird | Atrichornis clamosus | Noisy Scrub-bird | Atrichornis clamosus | nosbir1 |
| Rufous Scrubbird | Atrichornis rufescens | Rufous Scrub-bird | Atrichornis rufescens | rusbir1 |
| Southern Emerald Toucanet | Aulacorhynchus albivitta | Southern Emerald-Toucanet | Aulacorhynchus albivitta | souemt1 |
| Northern Emerald Toucanet | Aulacorhynchus prasinus | Northern Emerald-Toucanet | Aulacorhynchus prasinus | noremt1 |
| Black Crowned Crane | Balearica pavonina | Black Crowned-Crane | Balearica pavonina | blccra1 |
| Mountain Bamboo Partridge | Bambusicola fytchii | Mountain Bamboo-Partridge | Bambusicola fytchii | mobpar1 |
| Taiwan Bamboo Partridge | Bambusicola sonorivox | Taiwan Bamboo-Partridge | Bambusicola sonorivox | taibap1 |
| Chinese Bamboo Partridge | Bambusicola thoracicus | Chinese Bamboo-Partridge | Bambusicola thoracicus | chbpar3 |
| Black-headed Rufous Warbler | Bathmocercus cerviniventris | Black-headed Rufous-Warbler | Bathmocercus cerviniventris | bkcruw1 |
| Black-faced Rufous Warbler | Bathmocercus rufus | Black-faced Rufous-Warbler | Bathmocercus rufus | bkfruw1 |
| Short-legged Ground Roller | Brachypteracias leptosomus | Short-legged Ground-Roller | Brachypteracias leptosomus | slgrol1 |
| Cinnamon Bracken Warbler | Bradypterus cinnamomeus | Cinnamon Bracken-Warbler | Bradypterus cinnamomeus | cibwar1 |
| Evergreen Forest Warbler | Bradypterus lopezi | Evergreen-forest Warbler | Bradypterus lopezi | camscw1 |
| White-billed Buffalo Weaver | Bubalornis albirostris | White-billed Buffalo-Weaver | Bubalornis albirostris | wbbwea1 |
| Red-billed Buffalo Weaver | Bubalornis niger | Red-billed Buffalo-Weaver | Bubalornis niger | rbbwea1 |
| Blakiston's Fish Owl | Ketupa blakistoni | Blakiston's Fish-Owl | Ketupa blakistoni | blafio4 |
| Eastern Cattle Egret | Ardea coromanda | Eastern Cattle-Egret | Ardea coromanda | categr2 |
| Southern Ground Hornbill | Bucorvus leadbeateri | Southern Ground-Hornbill | Bucorvus leadbeateri | soghor1 |
| Papyrus Yellow Warbler | Calamonastides gracilirostris | Papyrus Yellow-Warbler | Calamonastides gracilirostris | paywar1 |
| Red-tailed Black Cockatoo | Calyptorhynchus banksii | Red-tailed Black-Cockatoo | Calyptorhynchus banksii | rtbcoc1 |
| Glossy Black Cockatoo | Calyptorhynchus lathami | Glossy Black-Cockatoo | Calyptorhynchus lathami | glbcoc1 |
| Small Tree Finch | Camarhynchus parvulus | Small Tree-Finch | Camarhynchus parvulus | smtfin1 |
| Medium Tree Finch | Camarhynchus pauper | Medium Tree-Finch | Camarhynchus pauper | metfin1 |
| Large Tree Finch | Camarhynchus psittacula | Large Tree-Finch | Camarhynchus psittacula | latfin1 |
| Northern Beardless Tyrannulet | Camptostoma imberbe | Northern Beardless-Tyrannulet | Camptostoma imberbe | nobtyr |
| Bornean Ground Cuckoo | Carpococcyx radiceus | Bornean Ground-Cuckoo | Carpococcyx radiceus | bogcuc1 |
| Coral-billed Ground Cuckoo | Carpococcyx renauldi | Coral-billed Ground-Cuckoo | Carpococcyx renauldi | cbgcuc1 |
| Sumatran Ground Cuckoo | Carpococcyx viridis | Sumatran Ground-Cuckoo | Carpococcyx viridis | sugcuc1 |
| Miombo Scrub Robin | Tychaedon barbata | Miombo Scrub-Robin | Tychaedon barbata | misrob1 |
| Rufous-tailed Scrub Robin | Cercotrichas galactotes | Rufous-tailed Scrub-Robin | Cercotrichas galactotes | rutscr1 |
| Brown-backed Scrub Robin | Cercotrichas hartlaubi | Brown-backed Scrub-Robin | Cercotrichas hartlaubi | bbsrob1 |
| White-browed Scrub Robin | Cercotrichas leucophrys | White-browed Scrub-Robin | Cercotrichas leucophrys | rbsrob1 |
| Forest Scrub Robin | Tychaedon leucosticta | Forest Scrub-Robin | Tychaedon leucosticta | fosrob1 |
| Kalahari Scrub Robin | Cercotrichas paena | Kalahari Scrub-Robin | Cercotrichas paena | kasrob1 |
| Black Scrub Robin | Cercotrichas podobe | Black Scrub-Robin | Cercotrichas podobe | blsrob1 |
| Bearded Scrub Robin | Tychaedon quadrivirgata | Bearded Scrub-Robin | Tychaedon quadrivirgata | besrob1 |
| Brown Scrub Robin | Tychaedon signata | Brown Scrub-Robin | Tychaedon signata | brsrob1 |
| Black-backed Dwarf Kingfisher | Ceyx erithaca | Black-backed Dwarf-Kingfisher | Ceyx erithaca | bkbkin1 |
| Rufous-backed Dwarf Kingfisher | Ceyx rufidorsa | Rufous-backed Dwarf-Kingfisher | Ceyx rufidorsa | rubkin1 |
| Sulawesi Dwarf Kingfisher | Ceyx fallax | Sulawesi Dwarf-Kingfisher | Ceyx fallax | sulkin1 |
| Moluccan Dwarf Kingfisher | Ceyx lepidus | Moluccan Dwarf-Kingfisher | Ceyx lepidus | varkin1 |
| Dimorphic Dwarf Kingfisher | Ceyx margarethae | Dimorphic Dwarf-Kingfisher | Ceyx margarethae | vardwk1 |
| Philippine Dwarf Kingfisher | Ceyx melanurus | Philippine Dwarf-Kingfisher | Ceyx melanurus | phikin1 |
| Papuan Dwarf Kingfisher | Ceyx solitarius | Papuan Dwarf-Kingfisher | Ceyx solitarius | vardwk6 |
| Horsfield's Bronze Cuckoo | Chalcites basalis | Horsfield's Bronze-Cuckoo | Chalcites basalis | hobcuc1 |
| Shining Bronze Cuckoo | Chalcites lucidus | Shining Bronze-Cuckoo | Chalcites lucidus | shbcuc1 |
| Little Bronze Cuckoo | Chalcites minutillus | Little Bronze-Cuckoo | Chalcites minutillus | libcuc1 |
| Rufous-throated Bronze Cuckoo | Chalcites ruficollis | Rufous-throated Bronze-Cuckoo | Chalcites ruficollis | rtbcuc1 |
| Fruithunter | Chlamydochaera jefferyi | Fruit-hunter | Chlamydochaera jefferyi | fruith1 |
| Mountain Blackeye | Zosterops emiliae | Mountain Black-eye | Zosterops emiliae | mouble1 |
| White-eared Bronze Cuckoo | Chalcites meyerii | White-eared Bronze-Cuckoo | Chalcites meyerii | webcuc1 |
| Collared Palm Thrush | Cichladusa arquata | Collared Palm-Thrush | Cichladusa arquata | copthr1 |
| Spotted Palm Thrush | Cichladusa guttata | Spotted Palm-Thrush | Cichladusa guttata | spmthr1 |
| Rufous-tailed Palm Thrush | Cichladusa ruficauda | Rufous-tailed Palm-Thrush | Cichladusa ruficauda | rtpthr1 |
| Western Banded Snake Eagle | Circaetus cinerascens | Western Banded Snake-Eagle | Circaetus cinerascens | baseag1 |
| Brown Snake Eagle | Circaetus cinereus | Brown Snake-Eagle | Circaetus cinereus | brseag1 |
| Southern Banded Snake Eagle | Circaetus fasciolatus | Southern Banded Snake-Eagle | Circaetus fasciolatus | faseag1 |
| Short-toed Snake Eagle | Circaetus gallicus | Short-toed Snake-Eagle | Circaetus gallicus | shteag1 |
| Common Green Magpie | Cissa chinensis | Common Green-Magpie | Cissa chinensis | gremag1 |
| Indochinese Green Magpie | Cissa hypoleuca | Indochinese Green-Magpie | Cissa hypoleuca | yebmag1 |
| Bornean Green Magpie | Cissa jefferyi | Bornean Green-Magpie | Cissa jefferyi | borgrm1 |
| Red-rumped Bush Tyrant | Cnemarchus erythropygius | Red-rumped Bush-Tyrant | Cnemarchus erythropygius | rrbtyr1 |
| Rufous-webbed Bush Tyrant | Cnemarchus rufipennis | Rufous-webbed Bush-Tyrant | Cnemarchus rufipennis | rwbtyr1 |
| Hispaniolan Lizard Cuckoo | Coccyzus longirostris | Hispaniolan Lizard-Cuckoo | Coccyzus longirostris | hislic1 |
| Great Lizard Cuckoo | Coccyzus merlini | Great Lizard-Cuckoo | Coccyzus merlini | grelic1 |
| Jamaican Lizard Cuckoo | Coccyzus vetula | Jamaican Lizard-Cuckoo | Coccyzus vetula | jamlic1 |
| Puerto Rican Lizard Cuckoo | Coccyzus vieilloti | Puerto Rican Lizard-Cuckoo | Coccyzus vieilloti | purlic1 |
| Nilgiri Wood Pigeon | Columba elphinstonii | Nilgiri Wood-Pigeon | Columba elphinstonii | niwpig1 |
| Black Wood Pigeon | Columba janthina | Black Wood-Pigeon | Columba janthina | jawpig1 |
| Andaman Wood Pigeon | Columba palumboides | Andaman Wood-Pigeon | Columba palumboides | anwpig1 |
| Common Wood Pigeon | Columba palumbus | Common Wood-Pigeon | Columba palumbus | cowpig1 |
| Ashy Wood Pigeon | Columba pulchricollis | Ashy Wood-Pigeon | Columba pulchricollis | aswpig1 |
| Sri Lanka Wood Pigeon | Columba torringtoniae | Sri Lanka Wood-Pigeon | Columba torringtoniae | ceywop1 |
| Western Wood Pewee | Contopus sordidulus | Western Wood-Pewee | Contopus sordidulus | wewpew |
| Eastern Wood Pewee | Contopus virens | Eastern Wood-Pewee | Contopus virens | eawpew |
| Cuban Palm Crow | Corvus minutus | Cuban Palm-Crow | Corvus minutus | cupcro1 |
| Hispaniolan Palm Crow | Corvus palmarum | Hispaniolan Palm-Crow | Corvus palmarum | palcro1 |
| Western Bearded Greenbul | Criniger barbatus | Western Bearded-Greenbul | Criniger barbatus | wesbeg1 |
| Eastern Bearded Greenbul | Criniger chloronotus | Eastern Bearded-Greenbul | Criniger chloronotus | easbeg1 |
| Blue Eared Pheasant | Crossoptilon auritum | Blue Eared-Pheasant | Crossoptilon auritum | blephe1 |
| White Eared Pheasant | Crossoptilon crossoptilon | White Eared-Pheasant | Crossoptilon crossoptilon | whieap1 |
| Tibetan Eared Pheasant | Crossoptilon harmani | Tibetan Eared-Pheasant | Crossoptilon harmani | whieap2 |
| Brown Eared Pheasant | Crossoptilon mantchuricum | Brown Eared-Pheasant | Crossoptilon mantchuricum | brephe1 |
| Double-eyed Fig Parrot | Cyclopsitta diophthalma | Double-eyed Fig-Parrot | Cyclopsitta diophthalma | defpar1 |
| Mindanao Pygmy Babbler | Dasycrotapha plateni | Mindanao Pygmy-Babbler | Dasycrotapha plateni | pygbab1 |
| Asian House Martin | Delichon dasypus | Asian House-Martin | Delichon dasypus | ashmar1 |
| Siberian House Martin | Delichon lagopodum | Siberian House-Martin | Delichon lagopodum | comhom2 |
| Western House Martin | Delichon urbicum | Western House-Martin | Delichon urbicum | comhom1 |
| Nepal House Martin | Delichon nipalense | Nepal House-Martin | Delichon nipalense | nephom1 |
| Amazonian Barred Woodcreeper | Dendrocolaptes certhia | Amazonian Barred-Woodcreeper | Dendrocolaptes certhia | amabaw1 |
| Northern Barred Woodcreeper | Dendrocolaptes sanctithomae | Northern Barred-Woodcreeper | Dendrocolaptes sanctithomae | nobwoo1 |
| West Indian Whistling Duck | Dendrocygna arborea | West Indian Whistling-Duck | Dendrocygna arborea | wiwduc1 |
| Wandering Whistling Duck | Dendrocygna arcuata | Wandering Whistling-Duck | Dendrocygna arcuata | wawduc1 |
| Black-bellied Whistling Duck | Dendrocygna autumnalis | Black-bellied Whistling-Duck | Dendrocygna autumnalis | bbwduc |
| Fulvous Whistling Duck | Dendrocygna bicolor | Fulvous Whistling-Duck | Dendrocygna bicolor | fuwduc |
| Plumed Whistling Duck | Dendrocygna eytoni | Plumed Whistling-Duck | Dendrocygna eytoni | plwduc1 |
| Spotted Whistling Duck | Dendrocygna guttata | Spotted Whistling-Duck | Dendrocygna guttata | spwduc1 |
| Lesser Whistling Duck | Dendrocygna javanica | Lesser Whistling-Duck | Dendrocygna javanica | lewduc1 |
| White-faced Whistling Duck | Dendrocygna viduata | White-faced Whistling-Duck | Dendrocygna viduata | wfwduc1 |
| Bearded Wood Partridge | Dendrortyx barbatus | Bearded Wood-Partridge | Dendrortyx barbatus | bewpar1 |
| Buffy-crowned Wood Partridge | Dendrortyx leucophrys | Buffy-crowned Wood-Partridge | Dendrortyx leucophrys | bcwpar1 |
| Long-tailed Wood Partridge | Dendrortyx macroura | Long-tailed Wood-Partridge | Dendrortyx macroura | ltwpar1 |
| White-headed Buffalo Weaver | Dinemellia dinemelli | White-headed Buffalo-Weaver | Dinemellia dinemelli | whbwea1 |
| Abyssinian Slaty Flycatcher | Melaenornis chocolatinus | Abyssinian Slaty-Flycatcher | Melaenornis chocolatinus | abyslf1 |
| White-eyed Slaty Flycatcher | Melaenornis fischeri | White-eyed Slaty-Flycatcher | Melaenornis fischeri | wheslf1 |
| Papuan Scrub Robin | Drymodes beccarii | Papuan Scrub-Robin | Drymodes beccarii | papscr2 |
| Southern Scrub Robin | Drymodes brunneopygia | Southern Scrub-Robin | Drymodes brunneopygia | sosrob1 |
| Northern Scrub Robin | Drymodes superciliaris | Northern Scrub-Robin | Drymodes superciliaris | nosrob1 |
| Green Imperial Pigeon | Ducula aenea | Green Imperial-Pigeon | Ducula aenea | gripig1 |
| Mountain Imperial Pigeon | Ducula badia | Mountain Imperial-Pigeon | Ducula badia | moipig1 |
| Malabar Imperial Pigeon | Ducula cuprea | Malabar Imperial-Pigeon | Ducula cuprea | mouimp1 |
| Vanuatu Imperial Pigeon | Ducula bakeri | Vanuatu Imperial-Pigeon | Ducula bakeri | baipig1 |
| Cinnamon-bellied Imperial Pigeon | Ducula basilica | Cinnamon-bellied Imperial-Pigeon | Ducula basilica | cbipig2 |
| Pied Imperial Pigeon | Ducula bicolor | Pied Imperial-Pigeon | Ducula bicolor | piipig1 |
| Chestnut-bellied Imperial Pigeon | Ducula brenchleyi | Chestnut-bellied Imperial-Pigeon | Ducula brenchleyi | cbipig1 |
| Rufescent Imperial Pigeon | Ducula chalconota | Rufescent Imperial-Pigeon | Ducula chalconota | rufimp1 |
| Elegant Imperial Pigeon | Ducula concinna | Elegant Imperial-Pigeon | Ducula concinna | elipig1 |
| Finsch's Imperial Pigeon | Ducula finschii | Finsch's Imperial-Pigeon | Ducula finschii | fiipig1 |
| White-bellied Imperial Pigeon | Ducula forsteni | White-bellied Imperial-Pigeon | Ducula forsteni | wbipig1 |
| Nuku Hiva Imperial Pigeon | Ducula galeata | Nuku Hiva Imperial-Pigeon | Ducula galeata | marimp1 |
| Geelvink Imperial Pigeon | Ducula geelvinkiana | Geelvink Imperial-Pigeon | Ducula geelvinkiana | spiimp2 |
| Dark-backed Imperial Pigeon | Ducula lacernulata | Dark-backed Imperial-Pigeon | Ducula lacernulata | dbipig1 |
| Barking Imperial Pigeon | Ducula latrans | Barking Imperial-Pigeon | Ducula latrans | peipig1 |
| Spice Imperial Pigeon | Ducula myristicivora | Spice Imperial-Pigeon | Ducula myristicivora | spipig1 |
| Seram Imperial Pigeon | Ducula neglecta | Seram Imperial-Pigeon | Ducula neglecta | wheimp1 |
| Micronesian Imperial Pigeon | Ducula oceanica | Micronesian Imperial-Pigeon | Ducula oceanica | miipig1 |
| Pacific Imperial Pigeon | Ducula pacifica | Pacific Imperial-Pigeon | Ducula pacifica | paipig1 |
| Spectacled Imperial Pigeon | Ducula perspicillata | Spectacled Imperial-Pigeon | Ducula perspicillata | wheimp2 |
| Pinon's Imperial Pigeon | Ducula pinon | Pinon's Imperial-Pigeon | Ducula pinon | piipig2 |
| Island Imperial Pigeon | Ducula pistrinaria | Island Imperial-Pigeon | Ducula pistrinaria | isipig1 |
| Pink-bellied Imperial Pigeon | Ducula poliocephala | Pink-bellied Imperial-Pigeon | Ducula poliocephala | pbipig1 |
| Pink-headed Imperial Pigeon | Ducula rosacea | Pink-headed Imperial-Pigeon | Ducula rosacea | phipig1 |
| Red-knobbed Imperial Pigeon | Ducula rubricera | Red-knobbed Imperial-Pigeon | Ducula rubricera | rkipig1 |
| Purple-tailed Imperial Pigeon | Ducula rufigaster | Purple-tailed Imperial-Pigeon | Ducula rufigaster | ptipig1 |
| Torresian Imperial Pigeon | Ducula spilorrhoa | Torresian Imperial-Pigeon | Ducula spilorrhoa | torimp1 |
| Zoe's Imperial Pigeon | Ducula zoeae | Zoe's Imperial-Pigeon | Ducula zoeae | zoeimp1 |
| Western Reef Heron | Egretta gularis | Western Reef-Heron | Egretta gularis | werher |
| Pacific Reef Heron | Egretta sacra | Pacific Reef-Heron | Egretta sacra | pacreh1 |
| Wedge-tailed Grass Finch | Emberizoides herbicola | Wedge-tailed Grass-Finch | Emberizoides herbicola | wtgfin1 |
| Lesser Grass Finch | Emberizoides ypiranganus | Lesser Grass-Finch | Emberizoides ypiranganus | lesgrf1 |
| Black-necklaced Scimitar Babbler | Erythrogenys erythrocnemis | Black-necklaced Scimitar-Babbler | Erythrogenys erythrocnemis | sbsbab2 |
| Black-streaked Scimitar Babbler | Erythrogenys gravivox | Black-streaked Scimitar-Babbler | Erythrogenys gravivox | bksscb1 |
| Large Scimitar Babbler | Erythrogenys hypoleucos | Large Scimitar-Babbler | Erythrogenys hypoleucos | lasbab1 |
| Spot-breasted Scimitar Babbler | Erythrogenys mcclellandi | Spot-breasted Scimitar-Babbler | Erythrogenys mcclellandi | spbscb1 |
| Elegant Crested Tinamou | Eudromia elegans | Elegant Crested-Tinamou | Eudromia elegans | elctin1 |
| Quebracho Crested Tinamou | Eudromia formosa | Quebracho Crested-Tinamou | Eudromia formosa | quctin1 |
| Fulvous-faced Scrub Tyrant | Euscarthmus fulviceps | Fulvous-faced Scrub-Tyrant | Euscarthmus fulviceps | tacpyt2 |
| Fulvous-crowned Scrub Tyrant | Euscarthmus meloryphus | Fulvous-crowned Scrub-Tyrant | Euscarthmus meloryphus | tacpyt1 |
| Rufous-sided Scrub Tyrant | Euscarthmus rufomarginatus | Rufous-sided Scrub-Tyrant | Euscarthmus rufomarginatus | rsptyr1 |
| Eastern Shriketit | Falcunculus frontatus | Eastern Shrike-tit | Falcunculus frontatus | cresht1 |
| Western Shriketit | Falcunculus leucogaster | Western Shrike-tit | Falcunculus leucogaster | cresht2 |
| Northern Shriketit | Falcunculus whitei | Northern Shrike-tit | Falcunculus whitei | cresht3 |
| Black-backed Water Tyrant | Fluvicola albiventer | Black-backed Water-Tyrant | Fluvicola albiventer | bbwtyr1 |
| Pied Water Tyrant | Fluvicola pica | Pied Water-Tyrant | Fluvicola pica | piwtyr1 |
| Masked Water Tyrant | Fluvicola nengeta | Masked Water-Tyrant | Fluvicola nengeta | mawtyr1 |
| White-browed Forest Flycatcher | Fraseria cinerascens | White-browed Forest-Flycatcher | Fraseria cinerascens | wbffly1 |
| Black-bellied Storm Petrel | Fregetta tropica | Black-bellied Storm-Petrel | Fregetta tropica | bbspet1 |
| Scaly Ground Roller | Geobiastes squamiger | Scaly Ground-Roller | Geobiastes squamiger | scagrr1 |
| Crossley's Ground Thrush | Geokichla crossleyi | Crossley's Ground-Thrush | Geokichla crossleyi | crgthr1 |
| Orange Ground Thrush | Geokichla gurneyi | Orange Ground-Thrush | Geokichla gurneyi | orgthr1 |
| Spotted Ground Thrush | Geokichla guttata | Spotted Ground-Thrush | Geokichla guttata | spgthr1 |
| Abyssinian Ground Thrush | Geokichla piaggiae | Abyssinian Ground-Thrush | Geokichla piaggiae | abgthr1 |
| Medium Ground Finch | Geospiza fortis | Medium Ground-Finch | Geospiza fortis | megfin1 |
| Small Ground Finch | Geospiza fuliginosa | Small Ground-Finch | Geospiza fuliginosa | smgfin1 |
| Large Ground Finch | Geospiza magnirostris | Large Ground-Finch | Geospiza magnirostris | lagfin1 |
| Common Cactus Finch | Geospiza scandens | Common Cactus-Finch | Geospiza scandens | cocfin3 |
| Yungas Pygmy Owl | Glaucidium bolivianum | Yungas Pygmy-Owl | Glaucidium bolivianum | yupowl1 |
| Ferruginous Pygmy Owl | Glaucidium brasilianum | Ferruginous Pygmy-Owl | Glaucidium brasilianum | fepowl |
| Costa Rican Pygmy Owl | Glaucidium costaricanum | Costa Rican Pygmy-Owl | Glaucidium costaricanum | crpowl |
| Northern Pygmy Owl | Glaucidium gnoma | Northern Pygmy-Owl | Glaucidium gnoma | nopowl |
| Central American Pygmy Owl | Glaucidium griseiceps | Central American Pygmy-Owl | Glaucidium griseiceps | capowl1 |
| Amazonian Pygmy Owl | Glaucidium hardyi | Amazonian Pygmy-Owl | Glaucidium hardyi | amapyo1 |
| Andean Pygmy Owl | Glaucidium jardinii | Andean Pygmy-Owl | Glaucidium jardinii | anpowl1 |
| Austral Pygmy Owl | Glaucidium nana | Austral Pygmy-Owl | Glaucidium nana | aupowl1 |
| Cloud-forest Pygmy Owl | Glaucidium nubicola | Cloud-forest Pygmy-Owl | Glaucidium nubicola | clopyo1 |
| Colima Pygmy Owl | Glaucidium palmarum | Colima Pygmy-Owl | Glaucidium palmarum | copowl1 |
| Subtropical Pygmy Owl | Glaucidium parkeri | Subtropical Pygmy-Owl | Glaucidium parkeri | supowl1 |
| Eurasian Pygmy Owl | Glaucidium passerinum | Eurasian Pygmy-Owl | Glaucidium passerinum | eupowl1 |
| Tamaulipas Pygmy Owl | Glaucidium sanchezi | Tamaulipas Pygmy-Owl | Glaucidium sanchezi | tapowl1 |
| Cuban Pygmy Owl | Glaucidium siju | Cuban Pygmy-Owl | Glaucidium siju | cupowl1 |
| Atlantic White Tern | Gygis alba | Atlantic White-Tern | Gygis alba | whiter3 |
| Duetting Giant Honeyeater | Gymnomyza brunneirostris | Duetting Giant-Honeyeater | Gymnomyza brunneirostris | duegih1 |
| Yellow-billed Giant Honeyeater | Gymnomyza viridis | Yellow-billed Giant-Honeyeater | Gymnomyza viridis | chagih1 |
| Black-cheeked Ant Tanager | Driophlox atrimaxillaris | Black-cheeked Ant-Tanager | Driophlox atrimaxillaris | bcatan1 |
| Crested Ant Tanager | Driophlox cristata | Crested Ant-Tanager | Driophlox cristata | cratan1 |
| Red-throated Ant Tanager | Driophlox fuscicauda | Red-throated Ant-Tanager | Driophlox fuscicauda | rtatan1 |
| Sooty Ant Tanager | Driophlox gutturalis | Sooty Ant-Tanager | Driophlox gutturalis | soatan1 |
| Red-crowned Ant Tanager | Habia rubica | Red-crowned Ant-Tanager | Habia rubica | rcatan1 |
| White-bellied Sea Eagle | Icthyophaga leucogaster | White-bellied Sea-Eagle | Icthyophaga leucogaster | wbseag1 |
| Pallas's Fish Eagle | Haliaeetus leucoryphus | Pallas's Fish-Eagle | Haliaeetus leucoryphus | pafeag1 |
| Steller's Sea Eagle | Haliaeetus pelagicus | Steller's Sea-Eagle | Haliaeetus pelagicus | stseag |
| African Fish Eagle | Icthyophaga vocifer | African Fish-Eagle | Icthyophaga vocifer | affeag1 |
| Madagascar Fish Eagle | Icthyophaga vociferoides | Madagascar Fish-Eagle | Icthyophaga vociferoides | mafeag1 |
| Hermit Wood Wren | Henicorhina anachoreta | Hermit Wood-Wren | Henicorhina anachoreta | gybwow3 |
| Bar-winged Wood Wren | Henicorhina leucoptera | Bar-winged Wood-Wren | Henicorhina leucoptera | bwwwre1 |
| White-breasted Wood Wren | Henicorhina leucosticta | White-breasted Wood-Wren | Henicorhina leucosticta | wbwwre1 |
| Munchique Wood Wren | Henicorhina negreti | Munchique Wood-Wren | Henicorhina negreti | munwow1 |
| Band-rumped Storm Petrel | Hydrobates castro | Band-rumped Storm-Petrel | Hydrobates castro | barpet |
| Fork-tailed Storm Petrel | Hydrobates furcatus | Fork-tailed Storm-Petrel | Hydrobates furcatus | ftspet |
| Ashy Storm Petrel | Hydrobates homochroa | Ashy Storm-Petrel | Hydrobates homochroa | asspet |
| Ringed Storm Petrel | Hydrobates hornbyi | Ringed Storm-Petrel | Hydrobates hornbyi | rispet1 |
| Leach's Storm Petrel | Hydrobates leucorhous | Leach's Storm-Petrel | Hydrobates leucorhous | lcspet |
| Markham's Storm Petrel | Hydrobates markhami | Markham's Storm-Petrel | Hydrobates markhami | maspet |
| Black Storm Petrel | Hydrobates melania | Black Storm-Petrel | Hydrobates melania | bkspet |
| Swinhoe's Storm Petrel | Hydrobates monorhis | Swinhoe's Storm-Petrel | Hydrobates monorhis | swspet |
| European Storm Petrel | Hydrobates pelagicus | European Storm-Petrel | Hydrobates pelagicus | bripet |
| Tristram's Storm Petrel | Hydrobates tristrami | Tristram's Storm-Petrel | Hydrobates tristrami | trspet |
| Javan Banded Pitta | Hydrornis guajanus | Javan Banded-Pitta | Hydrornis guajanus | banpit2 |
| Malayan Banded Pitta | Hydrornis irena | Malayan Banded-Pitta | Hydrornis irena | banpit3 |
| Bornean Banded Pitta | Hydrornis schwaneri | Bornean Banded-Pitta | Hydrornis schwaneri | banpit4 |
| Guianan Warbling Antbird | Hypocnemis cantator | Guianan Warbling-Antbird | Hypocnemis cantator | guiwaa1 |
| Imeri Warbling Antbird | Hypocnemis flavescens | Imeri Warbling-Antbird | Hypocnemis flavescens | imewaa1 |
| Rondonia Warbling Antbird | Hypocnemis ochrogyna | Rondonia Warbling-Antbird | Hypocnemis ochrogyna | ronwaa1 |
| Peruvian Warbling Antbird | Hypocnemis peruviana | Peruvian Warbling-Antbird | Hypocnemis peruviana | perwaa1 |
| Manicore Warbling Antbird | Hypocnemis rondoni | Manicore Warbling-Antbird | Hypocnemis rondoni | manwaa1 |
| Spix's Warbling Antbird | Hypocnemis striata | Spix's Warbling-Antbird | Hypocnemis striata | spiwaa1 |
| Yellow-breasted Warbling Antbird | Hypocnemis subflava | Yellow-breasted Warbling-Antbird | Hypocnemis subflava | yebwaa1 |
| Nuthatch Vanga | Hypositta corallirostris | Nuthatch-Vanga | Hypositta corallirostris | nuthat2 |
| Seram Golden Bulbul | Hypsipetes affinis | Seram Golden-Bulbul | Hypsipetes affinis | sergob1 |
| Banggai Golden Bulbul | Hypsipetes harterti | Banggai Golden-Bulbul | Hypsipetes harterti | sulgob2 |
| Sula Golden Bulbul | Hypsipetes longirostris | Sula Golden-Bulbul | Hypsipetes longirostris | sulgob3 |
| Obi Golden Bulbul | Hypsipetes lucasi | Obi Golden-Bulbul | Hypsipetes lucasi | obigob1 |
| Buru Golden Bulbul | Hypsipetes mysticalis | Buru Golden-Bulbul | Hypsipetes mysticalis | golbul4 |
| Lesser Fish Eagle | Icthyophaga humilis | Lesser Fish-Eagle | Icthyophaga humilis | lefeag1 |
| African Yellow Warbler | Iduna natalensis | African Yellow-Warbler | Iduna natalensis | afywar1 |
| Mountain Yellow Warbler | Iduna similis | Mountain Yellow-Warbler | Iduna similis | moywar1 |
| Buff-bridled Inca Finch | Incaspiza laeta | Buff-bridled Inca-Finch | Incaspiza laeta | bbifin1 |
| Rufous-backed Inca Finch | Incaspiza personata | Rufous-backed Inca-Finch | Incaspiza personata | rbifin1 |
| Great Inca Finch | Incaspiza pulchra | Great Inca-Finch | Incaspiza pulchra | grifin1 |
| Little Inca Finch | Incaspiza watkinsi | Little Inca-Finch | Incaspiza watkinsi | liifin1 |
| Short-tailed Scimitar Babbler | Napothera danjoui | Short-tailed Scimitar-Babbler | Napothera danjoui | stsbab1 |
| Tawny Fish Owl | Ketupa flavipes | Tawny Fish-Owl | Ketupa flavipes | tafowl1 |
| Buffy Fish Owl | Ketupa ketupu | Buffy Fish-Owl | Ketupa ketupu | bufowl2 |
| Brown Fish Owl | Ketupa zeylonensis | Brown Fish-Owl | Ketupa zeylonensis | brfowl1 |
| White-winged Black Tyrant | Knipolegus aterrimus | White-winged Black-Tyrant | Knipolegus aterrimus | whwblt1 |
| Blue-billed Black Tyrant | Knipolegus cyanirostris | Blue-billed Black-Tyrant | Knipolegus cyanirostris | bbbtyr1 |
| Hudson's Black Tyrant | Knipolegus hudsoni | Hudson's Black-Tyrant | Knipolegus hudsoni | hubtyr1 |
| Crested Black Tyrant | Knipolegus lophotes | Crested Black-Tyrant | Knipolegus lophotes | crbtyr1 |
| Velvety Black Tyrant | Knipolegus nigerrimus | Velvety Black-Tyrant | Knipolegus nigerrimus | vebtyr1 |
| Amazonian Black Tyrant | Knipolegus poecilocercus | Amazonian Black-Tyrant | Knipolegus poecilocercus | ambtyr1 |
| Amethyst-throated Mountaingem | Lampornis amethystinus | Amethyst-throated Mountain-gem | Lampornis amethystinus | amthum1 |
| Purple-throated Mountaingem | Lampornis calolaemus | Purple-throated Mountain-gem | Lampornis calolaemus | ptmgem |
| White-throated Mountaingem | Lampornis castaneoventris | White-throated Mountain-gem | Lampornis castaneoventris | wtmgem1 |
| Blue-throated Mountaingem | Lampornis clemenciae | Blue-throated Mountain-gem | Lampornis clemenciae | buthum |
| White-bellied Mountaingem | Lampornis hemileucus | White-bellied Mountain-gem | Lampornis hemileucus | wbmgem1 |
| Green-breasted Mountaingem | Lampornis sybillae | Green-breasted Mountain-gem | Lampornis sybillae | gbmgem1 |
| Green-throated Mountaingem | Lampornis viridipallens | Green-throated Mountain-gem | Lampornis viridipallens | gtmgem1 |
| Asian Rosy Finch | Leucosticte arctoa | Asian Rosy-Finch | Leucosticte arctoa | asrfin1 |
| Black Rosy Finch | Leucosticte atrata | Black Rosy-Finch | Leucosticte atrata | bkrfin |
| Brown-capped Rosy Finch | Leucosticte australis | Brown-capped Rosy-Finch | Leucosticte australis | bcrfin |
| Long-crested Pygmy Tyrant | Lophotriccus eulophotes | Long-crested Pygmy-Tyrant | Lophotriccus eulophotes | lcptyr1 |
| Helmeted Pygmy Tyrant | Lophotriccus galeatus | Helmeted Pygmy-Tyrant | Lophotriccus galeatus | heptyr1 |
| Scale-crested Pygmy Tyrant | Lophotriccus pileatus | Scale-crested Pygmy-Tyrant | Lophotriccus pileatus | scptyr1 |
| Double-banded Pygmy Tyrant | Lophotriccus vitiosus | Double-banded Pygmy-Tyrant | Lophotriccus vitiosus | dbptyr1 |
| Moluccan Hanging Parrot | Loriculus amabilis | Moluccan Hanging-Parrot | Loriculus amabilis | mohpar1 |
| Sri Lanka Hanging Parrot | Loriculus beryllinus | Sri Lanka Hanging-Parrot | Loriculus beryllinus | cehpar1 |
| Blue-crowned Hanging Parrot | Loriculus galgulus | Blue-crowned Hanging-Parrot | Loriculus galgulus | bchpar1 |
| Philippine Hanging Parrot | Loriculus philippensis | Philippine Hanging-Parrot | Loriculus philippensis | phihap1 |
| Sula Hanging Parrot | Loriculus sclateri | Sula Hanging-Parrot | Loriculus sclateri | sulhap1 |
| Vernal Hanging Parrot | Loriculus vernalis | Vernal Hanging-Parrot | Loriculus vernalis | vehpar1 |
| Woodlark | Lullula arborea | Wood Lark | Lullula arborea | woolar1 |
| Great Eared Nightjar | Lyncornis macrotis | Great Eared-Nightjar | Lyncornis macrotis | grenig1 |
| Southern Giant Petrel | Macronectes giganteus | Southern Giant-Petrel | Macronectes giganteus | angpet1 |
| Northern Giant Petrel | Macronectes halli | Northern Giant-Petrel | Macronectes halli | norgip1 |
| White-throated Screech Owl | Megascops albogularis | White-throated Screech-Owl | Megascops albogularis | whtsco1 |
| Eastern Screech Owl | Megascops asio | Eastern Screech-Owl | Megascops asio | easowl1 |
| Black-capped Screech Owl | Megascops atricapilla | Black-capped Screech-Owl | Megascops atricapilla | bkcsco1 |
| Bearded Screech Owl | Megascops barbarus | Bearded Screech-Owl | Megascops barbarus | besowl |
| Choco Screech Owl | Megascops centralis | Choco Screech-Owl | Megascops centralis | versco2 |
| Tropical Screech Owl | Megascops choliba | Tropical Screech-Owl | Megascops choliba | trsowl |
| Bare-shanked Screech Owl | Megascops clarkii | Bare-shanked Screech-Owl | Megascops clarkii | bssowl |
| Pacific Screech Owl | Megascops cooperi | Pacific Screech-Owl | Megascops cooperi | pasowl4 |
| Santa Marta Screech Owl | Megascops gilesi | Santa Marta Screech-Owl | Megascops gilesi | samsco1 |
| Middle American Screech Owl | Megascops guatemalae | Middle American Screech-Owl | Megascops guatemalae | vesowl |
| Rufescent Screech Owl | Megascops ingens | Rufescent Screech-Owl | Megascops ingens | rufsco1 |
| Western Screech Owl | Megascops kennicottii | Western Screech-Owl | Megascops kennicottii | wesowl1 |
| Koepcke's Screech Owl | Megascops koepckeae | Koepcke's Screech-Owl | Megascops koepckeae | koesco1 |
| Cloud-forest Screech Owl | Megascops marshalli | Cloud-forest Screech-Owl | Megascops marshalli | clfsco1 |
| Cinnamon Screech Owl | Megascops petersoni | Cinnamon Screech-Owl | Megascops petersoni | cinsco1 |
| Foothill Screech Owl | Megascops roraimae | Foothill Screech-Owl | Megascops roraimae | foosco1 |
| Long-tufted Screech Owl | Megascops sanctaecatarinae | Long-tufted Screech-Owl | Megascops sanctaecatarinae | lotsco1 |
| Balsas Screech Owl | Megascops seductus | Balsas Screech-Owl | Megascops seductus | basowl |
| Whiskered Screech Owl | Megascops trichopsis | Whiskered Screech-Owl | Megascops trichopsis | whsowl1 |
| Tawny-bellied Screech Owl | Megascops watsonii | Tawny-bellied Screech-Owl | Megascops watsonii | tabsco1 |
| Yellow-eyed Black Flycatcher | Melaenornis ardesiacus | Yellow-eyed Black-Flycatcher | Melaenornis ardesiacus | yebfly2 |
| Northern Black Flycatcher | Melaenornis edolioides | Northern Black-Flycatcher | Melaenornis edolioides | nobfly1 |
| Southern Black Flycatcher | Melaenornis pammelaina | Southern Black-Flycatcher | Melaenornis pammelaina | sobfly1 |
| White-shouldered Black Tit | Melaniparus guineensis | White-shouldered Black-Tit | Melaniparus guineensis | whsblt1 |
| White-winged Black Tit | Melaniparus leucomelas | White-winged Black-Tit | Melaniparus leucomelas | whwblt3 |
| White-backed Black Tit | Melaniparus leuconotus | White-backed Black-Tit | Melaniparus leuconotus | whbblt1 |
| Southern Black Tit | Melaniparus niger | Southern Black-Tit | Melaniparus niger | soublt1 |
| Pale Chanting Goshawk | Melierax canorus | Pale Chanting-Goshawk | Melierax canorus | pacgos1 |
| Dark Chanting Goshawk | Melierax metabates | Dark Chanting-Goshawk | Melierax metabates | dacgos1 |
| Eastern Chanting Goshawk | Melierax poliopterus | Eastern Chanting-Goshawk | Melierax poliopterus | eacgos1 |
| Moustached Grass Warbler | Melocichla mentalis | Moustached Grass-Warbler | Melocichla mentalis | mogwar1 |
| Cabanis's Ground Sparrow | Melozone cabanisi | Cabanis's Ground-Sparrow | Melozone cabanisi | pregrs2 |
| Rusty-crowned Ground Sparrow | Melozone kieneri | Rusty-crowned Ground-Sparrow | Melozone kieneri | rcgspa1 |
| White-eared Ground Sparrow | Melozone leucotis | White-eared Ground-Sparrow | Melozone leucotis | whegrs2 |
| Buckley's Forest Falcon | Micrastur buckleyi | Buckley's Forest-Falcon | Micrastur buckleyi | buffal1 |
| Lined Forest Falcon | Micrastur gilvicollis | Lined Forest-Falcon | Micrastur gilvicollis | liffal1 |
| Cryptic Forest Falcon | Micrastur mintoni | Cryptic Forest-Falcon | Micrastur mintoni | cryfof1 |
| Slaty-backed Forest Falcon | Micrastur mirandollei | Slaty-backed Forest-Falcon | Micrastur mirandollei | sbffal1 |
| Plumbeous Forest Falcon | Micrastur plumbeus | Plumbeous Forest-Falcon | Micrastur plumbeus | plffal1 |
| Barred Forest Falcon | Micrastur ruficollis | Barred Forest-Falcon | Micrastur ruficollis | baffal1 |
| Collared Forest Falcon | Micrastur semitorquatus | Collared Forest-Falcon | Micrastur semitorquatus | coffal1 |
| Jacky Winter | Microeca fascinans | Jacky-winter | Microeca fascinans | jacwin1 |
| Red-breasted Pygmy Parrot | Micropsitta bruijnii | Red-breasted Pygmy-Parrot | Micropsitta bruijnii | rbppar1 |
| Finsch's Pygmy Parrot | Micropsitta finschii | Finsch's Pygmy-Parrot | Micropsitta finschii | fippar1 |
| Yellow-capped Pygmy Parrot | Micropsitta keiensis | Yellow-capped Pygmy-Parrot | Micropsitta keiensis | ycppar1 |
| Buff-faced Pygmy Parrot | Micropsitta pusio | Buff-faced Pygmy-Parrot | Micropsitta pusio | bfppar1 |
| Jerdon's Bush Lark | Plocealauda affinis | Jerdon's Bushlark | Plocealauda affinis | jerbus2 |
| Bengal Bush Lark | Plocealauda assamica | Bengal Bushlark | Plocealauda assamica | benbus1 |
| Indochinese Bush Lark | Plocealauda erythrocephala | Indochinese Bushlark | Plocealauda erythrocephala | indbus3 |
| Indian Bush Lark | Plocealauda erythroptera | Indian Bushlark | Plocealauda erythroptera | indbus2 |
| Singing Bush Lark | Mirafra javanica | Singing Bushlark | Mirafra javanica | sinbus6 |
| Burmese Bush Lark | Plocealauda microptera | Burmese Bushlark | Plocealauda microptera | burbus1 |
| Olive Tufted Flycatcher | Mitrephanes olivaceus | Olive Tufted-Flycatcher | Mitrephanes olivaceus | olifly2 |
| Miombo Rock Thrush | Monticola angolensis | Miombo Rock-Thrush | Monticola angolensis | mirthr1 |
| Blue-capped Rock Thrush | Monticola cinclorhyncha | Blue-capped Rock-Thrush | Monticola cinclorhyncha | bcrthr1 |
| Sentinel Rock Thrush | Monticola explorator | Sentinel Rock-Thrush | Monticola explorator | serthr1 |
| White-throated Rock Thrush | Monticola gularis | White-throated Rock-Thrush | Monticola gularis | wtrthr1 |
| Littoral Rock Thrush | Monticola imerina | Littoral Rock-Thrush | Monticola imerina | litrot1 |
| Chestnut-bellied Rock Thrush | Monticola rufiventris | Chestnut-bellied Rock-Thrush | Monticola rufiventris | cbrthr1 |
| Little Rock Thrush | Monticola rufocinereus | Little Rock-Thrush | Monticola rufocinereus | lirthr1 |
| Cape Rock Thrush | Monticola rupestris | Cape Rock-Thrush | Monticola rupestris | carthr1 |
| White-winged Cliff Chat | Monticola semirufus | White-winged Cliff-Chat | Monticola semirufus | wwccha1 |
| Forest Rock Thrush | Monticola sharpei | Forest Rock-Thrush | Monticola sharpei | forrot2 |
| Blue Rock Thrush | Monticola solitarius | Blue Rock-Thrush | Monticola solitarius | burthr |
| Lesser Ground Cuckoo | Morococcyx erythropygus | Lesser Ground-Cuckoo | Morococcyx erythropygus | legcuc1 |
| Southern Sooty Woodpecker | Mulleripicus fuliginosus | Southern Sooty-Woodpecker | Mulleripicus fuliginosus | sousow1 |
| Northern Sooty Woodpecker | Mulleripicus funebris | Northern Sooty-Woodpecker | Mulleripicus funebris | soowoo1 |
| White-fronted Ground Tyrant | Muscisaxicola albifrons | White-fronted Ground-Tyrant | Muscisaxicola albifrons | wfgtyr1 |
| White-browed Ground Tyrant | Muscisaxicola albilora | White-browed Ground-Tyrant | Muscisaxicola albilora | wbgtyr1 |
| Cinnamon-bellied Ground Tyrant | Muscisaxicola capistratus | Cinnamon-bellied Ground-Tyrant | Muscisaxicola capistratus | cibgrt1 |
| Cinereous Ground Tyrant | Muscisaxicola cinereus | Cinereous Ground-Tyrant | Muscisaxicola cinereus | cingrt1 |
| Ochre-naped Ground Tyrant | Muscisaxicola flavinucha | Ochre-naped Ground-Tyrant | Muscisaxicola flavinucha | ongtyr1 |
| Black-fronted Ground Tyrant | Muscisaxicola frontalis | Black-fronted Ground-Tyrant | Muscisaxicola frontalis | bfgtyr1 |
| Puna Ground Tyrant | Muscisaxicola juninensis | Puna Ground-Tyrant | Muscisaxicola juninensis | pugtyr1 |
| Dark-faced Ground Tyrant | Muscisaxicola maclovianus | Dark-faced Ground-Tyrant | Muscisaxicola maclovianus | dafgrt1 |
| Spot-billed Ground Tyrant | Muscisaxicola maculirostris | Spot-billed Ground-Tyrant | Muscisaxicola maculirostris | sbgtyr1 |
| Rufous-naped Ground Tyrant | Muscisaxicola rufivertex | Rufous-naped Ground-Tyrant | Muscisaxicola rufivertex | rngtyr1 |
| White-bellied Pygmy Tyrant | Myiornis albiventris | White-bellied Pygmy-Tyrant | Myiornis albiventris | wbptyr1 |
| Black-capped Pygmy Tyrant | Myiornis atricapillus | Black-capped Pygmy-Tyrant | Myiornis atricapillus | bcptyr1 |
| Eared Pygmy Tyrant | Myiornis auricularis | Eared Pygmy-Tyrant | Myiornis auricularis | eaptyr1 |
| Short-tailed Pygmy Tyrant | Myiornis ecaudatus | Short-tailed Pygmy-Tyrant | Myiornis ecaudatus | stptyr1 |
| Smoky Bush Tyrant | Myiotheretes fumigatus | Smoky Bush-Tyrant | Myiotheretes fumigatus | smbtyr2 |
| Rufous-bellied Bush Tyrant | Myiotheretes fuscorufus | Rufous-bellied Bush-Tyrant | Myiotheretes fuscorufus | rbbtyr1 |
| Santa Marta Bush Tyrant | Myiotheretes pernix | Santa Marta Bush-Tyrant | Myiotheretes pernix | smbtyr1 |
| Streak-throated Bush Tyrant | Myiotheretes striaticollis | Streak-throated Bush-Tyrant | Myiotheretes striaticollis | stbtyr1 |
| Sri Lanka Whistling Thrush | Myophonus blighi | Sri Lanka Whistling-Thrush | Myophonus blighi | ceywht1 |
| Bornean Whistling Thrush | Myophonus borneensis | Bornean Whistling-Thrush | Myophonus borneensis | borwht1 |
| Javan Whistling Thrush | Myophonus glaucinus | Javan Whistling-Thrush | Myophonus glaucinus | javwht1 |
| Malabar Whistling Thrush | Myophonus horsfieldii | Malabar Whistling-Thrush | Myophonus horsfieldii | mawthr1 |
| Taiwan Whistling Thrush | Myophonus insularis | Taiwan Whistling-Thrush | Myophonus insularis | fowthr1 |
| Shiny Whistling Thrush | Myophonus melanurus | Shiny Whistling-Thrush | Myophonus melanurus | shwthr1 |
| Amazonian Streaked Antwren | Myrmotherula multostriata | Amazonian Streaked-Antwren | Myrmotherula multostriata | amasta1 |
| Guianan Streaked Antwren | Myrmotherula surinamensis | Guianan Streaked-Antwren | Myrmotherula surinamensis | guista1 |
| Dusky-cheeked Fig Parrot | Nannopsittacus melanogenia | Dusky-cheeked Fig-Parrot | Nannopsittacus melanogenia | orbfip1 |
| White-tailed Ant Thrush | Neocossyphus poensis | White-tailed Ant-Thrush | Neocossyphus poensis | wtathr1 |
| Red-tailed Ant Thrush | Neocossyphus rufus | Red-tailed Ant-Thrush | Neocossyphus rufus | rtathr1 |
| Rufous-vented Ground Cuckoo | Neomorphus geoffroyi | Rufous-vented Ground-Cuckoo | Neomorphus geoffroyi | rvgcuc1 |
| Red-billed Ground Cuckoo | Neomorphus pucheranii | Red-billed Ground-Cuckoo | Neomorphus pucheranii | rbgcuc1 |
| Banded Ground Cuckoo | Neomorphus radiolosus | Banded Ground-Cuckoo | Neomorphus radiolosus | bagcuc1 |
| Rufous-winged Ground Cuckoo | Neomorphus rufipennis | Rufous-winged Ground-Cuckoo | Neomorphus rufipennis | rwgcuc1 |
| Scaled Ground Cuckoo | Neomorphus squamiger | Scaled Ground-Cuckoo | Neomorphus squamiger | scgcuc1 |
| Subdesert Brush Warbler | Nesillas lantzii | Subdesert Brush-Warbler | Nesillas lantzii | subbrw1 |
| Malagasy Brush Warbler | Nesillas typica | Malagasy Brush-Warbler | Nesillas typica | malbrw1 |
| Malagasy Turtle Dove | Nesoenas picturatus | Malagasy Turtle-Dove | Nesoenas picturatus | matdov1 |
| African Pygmy Goose | Nettapus auritus | African Pygmy-Goose | Nettapus auritus | afrpyg1 |
| Cotton Pygmy Goose | Nettapus coromandelianus | Cotton Pygmy-Goose | Nettapus coromandelianus | copgoo1 |
| Green Pygmy Goose | Nettapus pulchellus | Green Pygmy-Goose | Nettapus pulchellus | grnpyg1 |
| Western Striolated Puffbird | Nystalus obamai | Western Striolated-Puffbird | Nystalus obamai | wespuf1 |
| Eastern Striolated Puffbird | Nystalus striolatus | Eastern Striolated-Puffbird | Nystalus striolatus | strpuf1 |
| Elliot's Storm Petrel | Oceanites gracilis | Elliot's Storm-Petrel | Oceanites gracilis | wvspet1 |
| Wilson's Storm Petrel | Oceanites oceanicus | Wilson's Storm-Petrel | Oceanites oceanicus | wispet |
| Pincoya Storm Petrel | Oceanites pincoyae | Pincoya Storm-Petrel | Oceanites pincoyae | pumstp1 |
| Black-fronted Wood Quail | Odontophorus atrifrons | Black-fronted Wood-Quail | Odontophorus atrifrons | bfwqua1 |
| Stripe-faced Wood Quail | Odontophorus balliviani | Stripe-faced Wood-Quail | Odontophorus balliviani | sfwqua1 |
| Spot-winged Wood Quail | Odontophorus capueira | Spot-winged Wood-Quail | Odontophorus capueira | swwqua1 |
| Venezuelan Wood Quail | Odontophorus columbianus | Venezuelan Wood-Quail | Odontophorus columbianus | venwoq1 |
| Tacarcuna Wood Quail | Odontophorus dialeucos | Tacarcuna Wood-Quail | Odontophorus dialeucos | tawqua1 |
| Rufous-fronted Wood Quail | Odontophorus erythrops | Rufous-fronted Wood-Quail | Odontophorus erythrops | rfwqua1 |
| Marbled Wood Quail | Odontophorus gujanensis | Marbled Wood-Quail | Odontophorus gujanensis | mawqua1 |
| Spotted Wood Quail | Odontophorus guttatus | Spotted Wood-Quail | Odontophorus guttatus | spwqua1 |
| Chestnut Wood Quail | Odontophorus hyperythrus | Chestnut Wood-Quail | Odontophorus hyperythrus | chwqua1 |
| Black-breasted Wood Quail | Odontophorus leucolaemus | Black-breasted Wood-Quail | Odontophorus leucolaemus | bbwqua1 |
| Dark-backed Wood Quail | Odontophorus melanonotus | Dark-backed Wood-Quail | Odontophorus melanonotus | dbwqua1 |
| Black-eared Wood Quail | Odontophorus melanotis | Black-eared Wood-Quail | Odontophorus melanotis | bewqua1 |
| Rufous-breasted Wood Quail | Odontophorus speciosus | Rufous-breasted Wood-Quail | Odontophorus speciosus | rbwqua1 |
| Starred Wood Quail | Odontophorus stellatus | Starred Wood-Quail | Odontophorus stellatus | stwqua1 |
| Gorgeted Wood Quail | Odontophorus strophium | Gorgeted Wood-Quail | Odontophorus strophium | gowqua1 |
| White-fronted Black Chat | Oenanthe albifrons | White-fronted Black-Chat | Oenanthe albifrons | wfbcha1 |
| Flores Scops Owl | Otus alfredi | Flores Scops-Owl | Otus alfredi | flsowl1 |
| Nicobar Scops Owl | Otus alius | Nicobar Scops-Owl | Otus alius | nicsco1 |
| Javan Scops Owl | Otus angelinae | Javan Scops-Owl | Otus angelinae | jasowl2 |
| Indian Scops Owl | Otus bakkamoena | Indian Scops-Owl | Otus bakkamoena | insowl1 |
| Andaman Scops Owl | Otus balli | Andaman Scops-Owl | Otus balli | ansowl1 |
| Biak Scops Owl | Otus beccarii | Biak Scops-Owl | Otus beccarii | biasco1 |
| Principe Scops Owl | Otus bikegila | Principe Scops-Owl | Otus bikegila | prisco1 |
| Rajah Scops Owl | Otus brookii | Rajah Scops-Owl | Otus brookii | rasowl1 |
| Pallid Scops Owl | Otus brucei | Pallid Scops-Owl | Otus brucei | pasowl3 |
| Anjouan Scops Owl | Otus capnodes | Anjouan Scops-Owl | Otus capnodes | ansowl2 |
| Sangihe Scops Owl | Otus collari | Sangihe Scops-Owl | Otus collari | sansco1 |
| Cyprus Scops Owl | Otus cyprius | Cyprus Scops-Owl | Otus cyprius | eursco3 |
| Ryukyu Scops Owl | Otus elegans | Ryukyu Scops-Owl | Otus elegans | ryusco1 |
| Everett's Scops Owl | Otus everetti | Everett's Scops-Owl | Otus everetti | evesco1 |
| African Scops Owl | Otus senegalensis | African Scops-Owl | Otus senegalensis | afsowl1 |
| Palawan Scops Owl | Otus fuliginosus | Palawan Scops-Owl | Otus fuliginosus | pasowl2 |
| Giant Scops Owl | Otus gurneyi | Giant Scops-Owl | Otus gurneyi | mineao1 |
| Sao Tome Scops Owl | Otus hartlaubi | Sao Tome Scops-Owl | Otus hartlaubi | stsowl1 |
| Sandy Scops Owl | Otus icterorhynchus | Sandy Scops-Owl | Otus icterorhynchus | sasowl1 |
| Seychelles Scops Owl | Otus insularis | Seychelles Scops-Owl | Otus insularis | sesowl1 |
| Sokoke Scops Owl | Otus ireneae | Sokoke Scops-Owl | Otus ireneae | sosowl1 |
| Rinjani Scops Owl | Otus jolandae | Rinjani Scops-Owl | Otus jolandae | rinsco1 |
| Luzon Scops Owl | Otus longicornis | Luzon Scops-Owl | Otus longicornis | lusowl1 |
| Moluccan Scops Owl | Otus magicus | Moluccan Scops-Owl | Otus magicus | mosowl1 |
| Sulawesi Scops Owl | Otus manadensis | Sulawesi Scops-Owl | Otus manadensis | susowl1 |
| Mantanani Scops Owl | Otus mantananensis | Mantanani Scops-Owl | Otus mantananensis | masowl2 |
| Philippine Scops Owl | Otus megalotis | Philippine Scops-Owl | Otus megalotis | phsowl1 |
| Banggai Scops Owl | Otus mendeni | Banggai Scops-Owl | Otus mendeni | sulsco5 |
| Mentawai Scops Owl | Otus mentawi | Mentawai Scops-Owl | Otus mentawi | mesowl1 |
| Mindanao Scops Owl | Otus mirus | Mindanao Scops-Owl | Otus mirus | misowl1 |
| Negros Scops Owl | Otus nigrorum | Negros Scops-Owl | Otus nigrorum | negsco1 |
| Arabian Scops Owl | Otus pamelae | Arabian Scops-Owl | Otus pamelae | arasco1 |
| Pemba Scops Owl | Otus pembaensis | Pemba Scops-Owl | Otus pembaensis | pesowl2 |
| Palau Scops Owl | Otus podarginus | Palau Scops-Owl | Otus podarginus | palowl2 |
| Reddish Scops Owl | Otus rufescens | Reddish Scops-Owl | Otus rufescens | resowl1 |
| Madagascar Scops Owl | Otus rutilus | Madagascar Scops-Owl | Otus rutilus | madsco1 |
| White-fronted Scops Owl | Otus sagittatus | White-fronted Scops-Owl | Otus sagittatus | wfsowl2 |
| Eurasian Scops Owl | Otus scops | Eurasian Scops-Owl | Otus scops | eursco1 |
| Japanese Scops Owl | Otus semitorques | Japanese Scops-Owl | Otus semitorques | jasowl1 |
| Wallace's Scops Owl | Otus silvicola | Wallace's Scops-Owl | Otus silvicola | wasowl1 |
| Socotra Scops Owl | Otus socotranus | Socotra Scops-Owl | Otus socotranus | afrsco2 |
| Mountain Scops Owl | Otus spilocephalus | Mountain Scops-Owl | Otus spilocephalus | mosowl2 |
| Sula Scops Owl | Otus sulaensis | Sula Scops-Owl | Otus sulaensis | sulsco3 |
| Oriental Scops Owl | Otus sunia | Oriental Scops-Owl | Otus sunia | orsowl |
| Serendib Scops Owl | Otus thilohoffmanni | Serendib Scops-Owl | Otus thilohoffmanni | sersco1 |
| Simeulue Scops Owl | Otus umbra | Simeulue Scops-Owl | Otus umbra | sisowl1 |
| Locust Finch | Paludipasser locustella | Locustfinch | Paludipasser locustella | locust3 |
| Common Diving Petrel | Pelecanoides urinatrix | Common Diving-Petrel | Pelecanoides urinatrix | codpet1 |
| Rock Bush Quail | Perdicula argoondah | Rock Bush-Quail | Perdicula argoondah | robqua1 |
| Jungle Bush Quail | Perdicula asiatica | Jungle Bush-Quail | Perdicula asiatica | jubqua1 |
| Painted Bush Quail | Perdicula erythrorhyncha | Painted Bush-Quail | Perdicula erythrorhyncha | pabqua1 |
| European Honey Buzzard | Pernis apivorus | European Honey-buzzard | Pernis apivorus | euhbuz1 |
| White-quilled Rock Pigeon | Petrophassa albipennis | White-quilled Rock-Pigeon | Petrophassa albipennis | wqrpig1 |
| Amethyst Brown Dove | Phapitreron amethystinus | Amethyst Brown-Dove | Phapitreron amethystinus | amedov1 |
| Mindanao Brown Dove | Phapitreron brunneiceps | Mindanao Brown-Dove | Phapitreron brunneiceps | daedov2 |
| Tawitawi Brown Dove | Phapitreron cinereiceps | Tawitawi Brown-Dove | Phapitreron cinereiceps | daedov3 |
| White-eared Brown Dove | Phapitreron leucotis | White-eared Brown-Dove | Phapitreron leucotis | whedov1 |
| Sri Lanka Bay Owl | Phodilus assimilis | Sri Lanka Bay-Owl | Phodilus assimilis | srlbao1 |
| Oriental Bay Owl | Phodilus badius | Oriental Bay-Owl | Phodilus badius | orbowl1 |
| Guianan Red Cotinga | Phoenicircus carnifex | Guianan Red-Cotinga | Phoenicircus carnifex | gurcot1 |
| Black-necked Red Cotinga | Phoenicircus nigricollis | Black-necked Red-Cotinga | Phoenicircus nigricollis | bnrcot1 |
| White-headed Wood Hoopoe | Phoeniculus bollei | White-headed Woodhoopoe | Phoeniculus bollei | whhwoo1 |
| Violet Wood Hoopoe | Phoeniculus damarensis | Violet Woodhoopoe | Phoeniculus damarensis | viowoo1 |
| Green Wood Hoopoe | Phoeniculus purpureus | Green Woodhoopoe | Phoeniculus purpureus | grewoo2 |
| Black-billed Wood Hoopoe | Phoeniculus somaliensis | Black-billed Woodhoopoe | Phoeniculus somaliensis | blbwoo2 |
| Toro Olive Greenbul | Phyllastrephus hypochloris | Toro Olive-Greenbul | Phyllastrephus hypochloris | toogre1 |
| Cameroon Olive Greenbul | Phyllastrephus poensis | Cameroon Olive-Greenbul | Phyllastrephus poensis | caogre1 |
| Chapman's Bristle Tyrant | Pogonotriccus chapmani | Chapman's Bristle-Tyrant | Pogonotriccus chapmani | chabrt1 |
| Southern Bristle Tyrant | Pogonotriccus eximius | Southern Bristle-Tyrant | Pogonotriccus eximius | sobtyr2 |
| Antioquia Bristle Tyrant | Pogonotriccus lanyoni | Antioquia Bristle-Tyrant | Pogonotriccus lanyoni | anbtyr1 |
| Marble-faced Bristle Tyrant | Pogonotriccus ophthalmicus | Marble-faced Bristle-Tyrant | Pogonotriccus ophthalmicus | mfbtyr1 |
| Spectacled Bristle Tyrant | Pogonotriccus orbitalis | Spectacled Bristle-Tyrant | Pogonotriccus orbitalis | spbtyr1 |
| Variegated Bristle Tyrant | Pogonotriccus poecilotis | Variegated Bristle-Tyrant | Pogonotriccus poecilotis | vabtyr1 |
| Venezuelan Bristle Tyrant | Pogonotriccus venezuelanus | Venezuelan Bristle-Tyrant | Pogonotriccus venezuelanus | vebtyr2 |
| Uganda Woodland Warbler | Phylloscopus budongoensis | Uganda Woodland-Warbler | Phylloscopus budongoensis | ugawow1 |
| Black-capped Woodland Warbler | Phylloscopus herberti | Black-capped Woodland-Warbler | Phylloscopus herberti | bcwwar1 |
| Red-faced Woodland Warbler | Phylloscopus laetus | Red-faced Woodland-Warbler | Phylloscopus laetus | rfwwar1 |
| Laura's Woodland Warbler | Phylloscopus laurae | Laura's Woodland-Warbler | Phylloscopus laurae | lauwow1 |
| Yellow-throated Woodland Warbler | Phylloscopus ruficapilla | Yellow-throated Woodland-Warbler | Phylloscopus ruficapilla | yetwow1 |
| Brown Woodland Warbler | Phylloscopus umbrovirens | Brown Woodland-Warbler | Phylloscopus umbrovirens | brwwar1 |
| Red-throated Piping Guan | Pipile cujubi | Red-throated Piping-Guan | Pipile cujubi | rtpgua1 |
| Blue-throated Piping Guan | Pipile cumanensis | Blue-throated Piping-Guan | Pipile cumanensis | butpig1 |
| White-throated Piping Guan | Pipile grayi | White-throated Piping-Guan | Pipile grayi | butpig2 |
| Black-fronted Piping Guan | Pipile jacutinga | Black-fronted Piping-Guan | Pipile jacutinga | bfpgua1 |
| Trinidad Piping Guan | Pipile pipile | Trinidad Piping-Guan | Pipile pipile | trpgua1 |
| Lesser Masked Weaver | Ploceus intermedius | Lesser Masked-Weaver | Ploceus intermedius | lesmaw1 |
| Northern Masked Weaver | Ploceus taeniopterus | Northern Masked-Weaver | Ploceus taeniopterus | nomwea1 |
| Southern Masked Weaver | Ploceus velatus | Southern Masked-Weaver | Ploceus velatus | afmwea |
| Vitelline Masked Weaver | Ploceus vitellinus | Vitelline Masked-Weaver | Ploceus vitellinus | vimwea1 |
| Holub's Golden Weaver | Ploceus xanthops | Holub's Golden-Weaver | Ploceus xanthops | hogwea1 |
| European Golden Plover | Pluvialis apricaria | European Golden-Plover | Pluvialis apricaria | eugplo |
| American Golden Plover | Pluvialis dominica | American Golden-Plover | Pluvialis dominica | amgplo |
| Pacific Golden Plover | Pluvialis fulva | Pacific Golden-Plover | Pluvialis fulva | pagplo |
| Mongolian Ground Jay | Podoces hendersoni | Mongolian Ground-Jay | Podoces hendersoni | mogjay1 |
| Turkestan Ground Jay | Podoces panderi | Turkestan Ground-Jay | Podoces panderi | tugjay1 |
| Iranian Ground Jay | Podoces pleskei | Iranian Ground-Jay | Podoces pleskei | irgjay1 |
| Serra do Mar Bristle Tyrant | Pogonotriccus difficilis | Serra do Mar Bristle-Tyrant | Pogonotriccus difficilis | sdmtyr2 |
| Sao Paulo Bristle Tyrant | Pogonotriccus paulista | Sao Paulo Bristle-Tyrant | Pogonotriccus paulista | saptyr1 |
| Sunda Scimitar Babbler | Pomatorhinus bornensis | Sunda Scimitar-Babbler | Pomatorhinus bornensis | chbscb2 |
| Black-crowned Scimitar Babbler | Pomatorhinus ferruginosus | Black-crowned Scimitar-Babbler | Pomatorhinus ferruginosus | cobscb1 |
| Indian Scimitar Babbler | Pomatorhinus horsfieldii | Indian Scimitar-Babbler | Pomatorhinus horsfieldii | insbab1 |
| Sri Lanka Scimitar Babbler | Pomatorhinus melanurus | Sri Lanka Scimitar-Babbler | Pomatorhinus melanurus | srlscb1 |
| Javan Scimitar Babbler | Pomatorhinus montanus | Javan Scimitar-Babbler | Pomatorhinus montanus | chbscb1 |
| Taiwan Scimitar Babbler | Pomatorhinus musicus | Taiwan Scimitar-Babbler | Pomatorhinus musicus | taiscb1 |
| Red-billed Scimitar Babbler | Pomatorhinus ochraceiceps | Red-billed Scimitar-Babbler | Pomatorhinus ochraceiceps | rbsbab1 |
| Brown-crowned Scimitar Babbler | Pomatorhinus phayrei | Brown-crowned Scimitar-Babbler | Pomatorhinus phayrei | bncscb1 |
| Streak-breasted Scimitar Babbler | Pomatorhinus ruficollis | Streak-breasted Scimitar-Babbler | Pomatorhinus ruficollis | sbsbab3 |
| White-browed Scimitar Babbler | Pomatorhinus schisticeps | White-browed Scimitar-Babbler | Pomatorhinus schisticeps | wbsbab1 |
| Slender-billed Scimitar Babbler | Pomatorhinus superciliaris | Slender-billed Scimitar-Babbler | Pomatorhinus superciliaris | sbsbab1 |
| Masked Shining Parrot | Prosopeia personata | Masked Shining-Parrot | Prosopeia personata | maspar2 |
| Crimson Shining Parrot | Prosopeia splendens | Crimson Shining-Parrot | Prosopeia splendens | crspar1 |
| Maroon Shining Parrot | Prosopeia tabuensis | Maroon Shining-Parrot | Prosopeia tabuensis | respar1 |
| Black-capped Social Weaver | Pseudonigrita cabanisi | Black-capped Social-Weaver | Pseudonigrita cabanisi | bcswea1 |
| Bronze-olive Pygmy Tyrant | Pseudotriccus pelzelni | Bronze-olive Pygmy-Tyrant | Pseudotriccus pelzelni | boptyr1 |
| Rufous-headed Pygmy Tyrant | Pseudotriccus ruficeps | Rufous-headed Pygmy-Tyrant | Pseudotriccus ruficeps | rhptyr1 |
| Hazel-fronted Pygmy Tyrant | Pseudotriccus simplex | Hazel-fronted Pygmy-Tyrant | Pseudotriccus simplex | hfptyr1 |
| Brehm's Tiger Parrot | Psittacella brehmii | Brehm's Tiger-Parrot | Psittacella brehmii | brtpar2 |
| Painted Tiger Parrot | Psittacella picta | Painted Tiger-Parrot | Psittacella picta | patpar1 |
| King of Saxony Bird-of-paradise | Pteridophora alberti | King-of-Saxony Bird-of-Paradise | Pteridophora alberti | kospar1 |
| Black-banded Fruit Dove | Ptilinopus alligator | Black-banded Fruit-Dove | Ptilinopus alligator | bbfdov2 |
| Orange-fronted Fruit Dove | Ptilinopus aurantiifrons | Orange-fronted Fruit-Dove | Ptilinopus aurantiifrons | offdov1 |
| Raiatea Fruit Dove | Ptilinopus chrysogaster | Raiatea Fruit-Dove | Ptilinopus chrysogaster | gygfrd2 |
| Coroneted Fruit Dove | Ptilinopus coronulatus | Coroneted Fruit-Dove | Ptilinopus coronulatus | cofdov1 |
| Red-naped Fruit Dove | Ptilinopus dohertyi | Red-naped Fruit-Dove | Ptilinopus dohertyi | rnfdov1 |
| White-capped Fruit Dove | Ptilinopus dupetithouarsii | White-capped Fruit-Dove | Ptilinopus dupetithouarsii | wcfdov1 |
| Red-bellied Fruit Dove | Ptilinopus greyi | Red-bellied Fruit-Dove | Ptilinopus greyi | rbfdov1 |
| Knob-billed Fruit Dove | Ptilinopus insolitus | Knob-billed Fruit-Dove | Ptilinopus insolitus | kbfdov1 |
| Orange-bellied Fruit Dove | Ptilinopus iozonus | Orange-bellied Fruit-Dove | Ptilinopus iozonus | obfdov1 |
| Black-naped Fruit Dove | Ptilinopus melanospilus | Black-naped Fruit-Dove | Ptilinopus melanospilus | bknfrd1 |
| Blue-capped Fruit Dove | Ptilinopus monacha | Blue-capped Fruit-Dove | Ptilinopus monacha | bcfdov2 |
| Dwarf Fruit Dove | Ptilinopus nainus | Dwarf Fruit-Dove | Ptilinopus nainus | dwafrd1 |
| Palau Fruit Dove | Ptilinopus pelewensis | Palau Fruit-Dove | Ptilinopus pelewensis | pafdov1 |
| Pink-spotted Fruit Dove | Ptilinopus perlatus | Pink-spotted Fruit-Dove | Ptilinopus perlatus | psfdov1 |
| Many-colored Fruit Dove | Ptilinopus perousii | Many-colored Fruit-Dove | Ptilinopus perousii | mcfdov1 |
| Purple-capped Fruit Dove | Ptilinopus ponapensis | Purple-capped Fruit-Dove | Ptilinopus ponapensis | pucfrd1 |
| Crimson-crowned Fruit Dove | Ptilinopus porphyraceus | Crimson-crowned Fruit-Dove | Ptilinopus porphyraceus | ccfdov1 |
| Pink-headed Fruit Dove | Ptilinopus porphyreus | Pink-headed Fruit-Dove | Ptilinopus porphyreus | phfdov1 |
| Beautiful Fruit Dove | Ptilinopus pulchellus | Beautiful Fruit-Dove | Ptilinopus pulchellus | befdov1 |
| Rose-crowned Fruit Dove | Ptilinopus regina | Rose-crowned Fruit-Dove | Ptilinopus regina | rcfdov1 |
| White-bibbed Fruit Dove | Ptilinopus rivoli | White-bibbed Fruit-Dove | Ptilinopus rivoli | whbfrd1 |
| Mariana Fruit Dove | Ptilinopus roseicapilla | Mariana Fruit-Dove | Ptilinopus roseicapilla | mafdov2 |
| Yellow-bibbed Fruit Dove | Ptilinopus solomonensis | Yellow-bibbed Fruit-Dove | Ptilinopus solomonensis | yebfrd2 |
| Geelvink Fruit Dove | Ptilinopus speciosus | Geelvink Fruit-Dove | Ptilinopus speciosus | yebfrd1 |
| Superb Fruit Dove | Ptilinopus superbus | Superb Fruit-Dove | Ptilinopus superbus | sufdov1 |
| Tanna Fruit Dove | Ptilinopus tannensis | Tanna Fruit-Dove | Ptilinopus tannensis | tafdov1 |
| Claret-breasted Fruit Dove | Ptilinopus viridis | Claret-breasted Fruit-Dove | Ptilinopus viridis | cbfdov1 |
| Wallace's Fruit Dove | Ptilinopus wallacii | Wallace's Fruit-Dove | Ptilinopus wallacii | wafdov1 |
| Dusky Crag Martin | Ptyonoprogne concolor | Dusky Crag-Martin | Ptyonoprogne concolor | duscrm1 |
| Pale Crag Martin | Ptyonoprogne obsoleta | Pale Crag-Martin | Ptyonoprogne obsoleta | rocmar1 |
| Eurasian Crag Martin | Ptyonoprogne rupestris | Eurasian Crag-Martin | Ptyonoprogne rupestris | eurcrm1 |
| Chinese Penduline Tit | Remiz consobrinus | Chinese Penduline-Tit | Remiz consobrinus | chptit1 |
| White-crowned Penduline Tit | Remiz coronatus | White-crowned Penduline-Tit | Remiz coronatus | wcptit1 |
| Black-headed Penduline Tit | Remiz macronyx | Black-headed Penduline-Tit | Remiz macronyx | bhptit1 |
| Eurasian Penduline Tit | Remiz pendulinus | Eurasian Penduline-Tit | Remiz pendulinus | euptit1 |
| Sunda Pied Fantail | Rhipidura javanica | Sunda Pied-Fantail | Rhipidura javanica | piefan1 |
| Willie Wagtail | Rhipidura leucophrys | Willie-wagtail | Rhipidura leucophrys | wilwag1 |
| White-bellied Thicket Fantail | Rhipidura leucothorax | White-bellied Thicket-Fantail | Rhipidura leucothorax | wbtfan1 |
| Black Thicket Fantail | Rhipidura maculipectus | Black Thicket-Fantail | Rhipidura maculipectus | bltfan1 |
| Philippine Pied Fantail | Rhipidura nigritorquis | Philippine Pied-Fantail | Rhipidura nigritorquis | phipif1 |
| Visayan Blue Fantail | Rhipidura samarensis | Visayan Blue-Fantail | Rhipidura samarensis | visblf1 |
| Mindanao Blue Fantail | Rhipidura superciliaris | Mindanao Blue-Fantail | Rhipidura superciliaris | blufan1 |
| Sooty Thicket Fantail | Rhipidura threnothorax | Sooty Thicket-Fantail | Rhipidura threnothorax | sotfan1 |
| Bicol Ground Warbler | Robsonius sorsogonensis | Bicol Ground-Warbler | Robsonius sorsogonensis | gybbab2 |
| Sierra Madre Ground Warbler | Robsonius thompsoni | Sierra Madre Ground-Warbler | Robsonius thompsoni | simgrw1 |
| Pied Bush Chat | Saxicola caprata | Pied Bushchat | Saxicola caprata | piebus1 |
| White-throated Bush Chat | Saxicola insignis | White-throated Bushchat | Saxicola insignis | whtbus1 |
| Jerdon's Bush Chat | Saxicola jerdoni | Jerdon's Bushchat | Saxicola jerdoni | jerbus1 |
| Streaked Scrub Warbler | Scotocerca inquieta | Streaked Scrub-Warbler | Scotocerca inquieta | stswar1 |
| Vermiculated Fishing Owl | Scotopelia bouvieri | Vermiculated Fishing-Owl | Scotopelia bouvieri | vefowl1 |
| Pel's Fishing Owl | Scotopelia peli | Pel's Fishing-Owl | Scotopelia peli | pefowl1 |
| Elfin Woods Warbler | Setophaga angelae | Elfin-woods Warbler | Setophaga angelae | elwwar1 |
| Greater Yellow Finch | Sicalis auriventris | Greater Yellow-Finch | Sicalis auriventris | gryfin2 |
| Stripe-tailed Yellow Finch | Sicalis citrina | Stripe-tailed Yellow-Finch | Sicalis citrina | styfin1 |
| Orange-fronted Yellow Finch | Sicalis columbiana | Orange-fronted Yellow-Finch | Sicalis columbiana | ofyfin1 |
| Patagonian Yellow Finch | Sicalis lebruni | Patagonian Yellow-Finch | Sicalis lebruni | payfin1 |
| Puna Yellow Finch | Sicalis lutea | Puna Yellow-Finch | Sicalis lutea | puyfin1 |
| Citron-headed Yellow Finch | Sicalis luteocephala | Citron-headed Yellow-Finch | Sicalis luteocephala | chyfin1 |
| Grassland Yellow Finch | Sicalis luteola | Grassland Yellow-Finch | Sicalis luteola | gryfin1 |
| Monte Yellow Finch | Sicalis mendozae | Monte Yellow-Finch | Sicalis mendozae | monyef1 |
| Greenish Yellow Finch | Sicalis olivascens | Greenish Yellow-Finch | Sicalis olivascens | gryfin3 |
| Raimondi's Yellow Finch | Sicalis raimondii | Raimondi's Yellow-Finch | Sicalis raimondii | rayfin1 |
| Bright-rumped Yellow Finch | Sicalis uropygialis | Bright-rumped Yellow-Finch | Sicalis uropygialis | bryfin1 |
| Crested Serpent Eagle | Spilornis cheela | Crested Serpent-Eagle | Spilornis cheela | crseag1 |
| Andaman Serpent Eagle | Spilornis elgini | Andaman Serpent-Eagle | Spilornis elgini | anseag1 |
| Philippine Serpent Eagle | Spilornis holospilus | Philippine Serpent-Eagle | Spilornis holospilus | phseag1 |
| Mountain Serpent Eagle | Spilornis kinabaluensis | Mountain Serpent-Eagle | Spilornis kinabaluensis | moseag1 |
| Sulawesi Serpent Eagle | Spilornis rufipectus | Sulawesi Serpent-Eagle | Spilornis rufipectus | suseag1 |
| Chestnut-bellied Seed Finch | Sporophila angolensis | Chestnut-bellied Seed-Finch | Sporophila angolensis | cbsfin |
| Black-billed Seed Finch | Sporophila atrirostris | Black-billed Seed-Finch | Sporophila atrirostris | bbsfin1 |
| Large-billed Seed Finch | Sporophila crassirostris | Large-billed Seed-Finch | Sporophila crassirostris | lbsfin1 |
| Thick-billed Seed Finch | Sporophila funerea | Thick-billed Seed-Finch | Sporophila funerea | tbsfin1 |
| Great-billed Seed Finch | Sporophila maximiliani | Great-billed Seed-Finch | Sporophila maximiliani | gbsfin1 |
| Nicaraguan Seed Finch | Sporophila nuttingi | Nicaraguan Seed-Finch | Sporophila nuttingi | nisfin1 |
| Southern Emu-wren | Stipiturus malachurus | Southern Emuwren | Stipiturus malachurus | souemu1 |
| Mallee Emu-wren | Stipiturus mallee | Mallee Emuwren | Stipiturus mallee | malemu1 |
| Rufous-crowned Emu-wren | Stipiturus ruficeps | Rufous-crowned Emuwren | Stipiturus ruficeps | rucemu1 |
| Philippine Collared Dove | Streptopelia dusumieri | Philippine Collared-Dove | Streptopelia dusumieri | phicod1 |
| Eurasian Collared Dove | Streptopelia decaocto | Eurasian Collared-Dove | Streptopelia decaocto | eucdov |
| Mourning Collared Dove | Streptopelia decipiens | Mourning Collared-Dove | Streptopelia decipiens | afmdov1 |
| Adamawa Turtle Dove | Streptopelia hypopyrrha | Adamawa Turtle-Dove | Streptopelia hypopyrrha | adtdov1 |
| Dusky Turtle Dove | Streptopelia lugens | Dusky Turtle-Dove | Streptopelia lugens | dutdov1 |
| Oriental Turtle Dove | Streptopelia orientalis | Oriental Turtle-Dove | Streptopelia orientalis | ortdov |
| White-winged Collared Dove | Streptopelia reichenowi | White-winged Collared-Dove | Streptopelia reichenowi | wwcdov1 |
| African Collared Dove | Streptopelia roseogrisea | African Collared-Dove | Streptopelia roseogrisea | afcdov1 |
| Red Collared Dove | Streptopelia tranquebarica | Red Collared-Dove | Streptopelia tranquebarica | recdov1 |
| European Turtle Dove | Streptopelia turtur | European Turtle-Dove | Streptopelia turtur | eutdov |
| Brown Wood Owl | Strix leptogrammica | Brown Wood-Owl | Strix leptogrammica | brwowl1 |
| Mottled Wood Owl | Strix ocellata | Mottled Wood-Owl | Strix ocellata | mowowl1 |
| Spotted Wood Owl | Strix seloputo | Spotted Wood-Owl | Strix seloputo | spwowl1 |
| African Wood Owl | Strix woodfordii | African Wood-Owl | Strix woodfordii | afwowl1 |
| Northern Scrub Flycatcher | Sublegatus arenarum | Northern Scrub-Flycatcher | Sublegatus arenarum | nosfly1 |
| Southern Scrub Flycatcher | Sublegatus modestus | Southern Scrub-Flycatcher | Sublegatus modestus | sosfly1 |
| Amazonian Scrub Flycatcher | Sublegatus obscurior | Amazonian Scrub-Flycatcher | Sublegatus obscurior | amsfly1 |
| Northern Hawk-Owl | Surnia ulula | Northern Hawk Owl | Surnia ulula | nohowl |
| Falkland Steamer Duck | Tachyeres brachypterus | Falkland Steamer-Duck | Tachyeres brachypterus | falstd1 |
| Flying Steamer Duck | Tachyeres patachonicus | Flying Steamer-Duck | Tachyeres patachonicus | flystd1 |
| Numfor Paradise Kingfisher | Tanysiptera carolinae | Numfor Paradise-Kingfisher | Tanysiptera carolinae | nupkin1 |
| Brown-headed Paradise Kingfisher | Tanysiptera danae | Brown-headed Paradise-Kingfisher | Tanysiptera danae | bhpkin1 |
| Little Paradise Kingfisher | Tanysiptera hydrocharis | Little Paradise-Kingfisher | Tanysiptera hydrocharis | lipkin1 |
| Black-capped Paradise Kingfisher | Tanysiptera nigriceps | Black-capped Paradise-Kingfisher | Tanysiptera nigriceps | bubpak2 |
| Red-breasted Paradise Kingfisher | Tanysiptera nympha | Red-breasted Paradise-Kingfisher | Tanysiptera nympha | rbpkin1 |
| Biak Paradise Kingfisher | Tanysiptera riedelii | Biak Paradise-Kingfisher | Tanysiptera riedelii | bipkin1 |
| Buff-breasted Paradise Kingfisher | Tanysiptera sylvia | Buff-breasted Paradise-Kingfisher | Tanysiptera sylvia | bubpak1 |
| Golden Bush Robin | Tarsiger chrysaeus | Golden Bush-Robin | Tarsiger chrysaeus | gobrob1 |
| Taiwan Bush Robin | Tarsiger formosanus | Taiwan Bush-Robin | Tarsiger formosanus | whbbur3 |
| Rufous-breasted Bush Robin | Tarsiger hyperythrus | Rufous-breasted Bush-Robin | Tarsiger hyperythrus | rbbrob1 |
| White-browed Bush Robin | Tarsiger indicus | White-browed Bush-Robin | Tarsiger indicus | wbbrob1 |
| Collared Bush Robin | Tarsiger johnstoniae | Collared Bush-Robin | Tarsiger johnstoniae | cobrob1 |
| Blyth's Paradise Flycatcher | Terpsiphone affinis | Blyth's Paradise-Flycatcher | Terpsiphone affinis | blypaf1 |
| Amur Paradise Flycatcher | Terpsiphone incei | Amur Paradise-Flycatcher | Terpsiphone incei | amupaf1 |
| Indian Paradise Flycatcher | Terpsiphone paradisi | Indian Paradise-Flycatcher | Terpsiphone paradisi | aspfly1 |
| Black Paradise Flycatcher | Terpsiphone atrocaudata | Black Paradise-Flycatcher | Terpsiphone atrocaudata | japfly1 |
| Sao Tome Paradise Flycatcher | Terpsiphone atrochalybeia | Sao Tome Paradise-Flycatcher | Terpsiphone atrochalybeia | stpfly1 |
| Mascarene Paradise Flycatcher | Terpsiphone bourbonnensis | Mascarene Paradise-Flycatcher | Terpsiphone bourbonnensis | mapfly2 |
| Rufous Paradise Flycatcher | Terpsiphone cinnamomea | Rufous Paradise-Flycatcher | Terpsiphone cinnamomea | rupfly1 |
| Seychelles Paradise Flycatcher | Terpsiphone corvina | Seychelles Paradise-Flycatcher | Terpsiphone corvina | sepfly1 |
| Blue Paradise Flycatcher | Terpsiphone cyanescens | Blue Paradise-Flycatcher | Terpsiphone cyanescens | blpfly1 |
| Tenggara Paradise Flycatcher | Terpsiphone floris | Tenggara Paradise-Flycatcher | Terpsiphone floris | blypaf3 |
| Malagasy Paradise Flycatcher | Terpsiphone mutata | Malagasy Paradise-Flycatcher | Terpsiphone mutata | mapfly1 |
| Red-bellied Paradise Flycatcher | Terpsiphone rufiventer | Red-bellied Paradise-Flycatcher | Terpsiphone rufiventer | bhpfly1 |
| Rufous-vented Paradise Flycatcher | Terpsiphone rufocinerea | Rufous-vented Paradise-Flycatcher | Terpsiphone rufocinerea | rvpfly1 |
| African Paradise Flycatcher | Terpsiphone viridis | African Paradise-Flycatcher | Terpsiphone viridis | afpfly1 |
| Mocking Cliff Chat | Thamnolaea cinnamomeiventris | Mocking Cliff-Chat | Thamnolaea cinnamomeiventris | moccha1 |
| Sooretama Slaty Antshrike | Thamnophilus ambiguus | Sooretama Slaty-Antshrike | Thamnophilus ambiguus | soosla1 |
| Planalto Slaty Antshrike | Thamnophilus pelzelni | Planalto Slaty-Antshrike | Thamnophilus pelzelni | plasla1 |
| Northern Slaty Antshrike | Thamnophilus punctatus | Northern Slaty-Antshrike | Thamnophilus punctatus | norsla1 |
| Natterer's Slaty Antshrike | Thamnophilus stictocephalus | Natterer's Slaty-Antshrike | Thamnophilus stictocephalus | natsla1 |
| Bolivian Slaty Antshrike | Thamnophilus sticturus | Bolivian Slaty-Antshrike | Thamnophilus sticturus | bolsla1 |
| White-crested Tiger Heron | Tigriornis leucolopha | White-crested Tiger-Heron | Tigriornis leucolopha | whcbit1 |
| Rufescent Tiger Heron | Tigrisoma lineatum | Rufescent Tiger-Heron | Tigrisoma lineatum | ruther1 |
| Bare-throated Tiger Heron | Tigrisoma mexicanum | Bare-throated Tiger-Heron | Tigrisoma mexicanum | btther1 |
| Pin-tailed Green Pigeon | Treron apicauda | Pin-tailed Green-Pigeon | Treron apicauda | pitpig1 |
| Madagascar Green Pigeon | Treron australis | Madagascar Green-Pigeon | Treron australis | madgrp1 |
| Philippine Green Pigeon | Treron axillaris | Philippine Green-Pigeon | Treron axillaris | pomgrp1 |
| Orange-breasted Green Pigeon | Treron bicinctus | Orange-breasted Green-Pigeon | Treron bicinctus | orbpig1 |
| African Green Pigeon | Treron calvus | African Green-Pigeon | Treron calvus | afrgrp1 |
| Large Green Pigeon | Treron capellei | Large Green-Pigeon | Treron capellei | lagpig1 |
| Andaman Green Pigeon | Treron chloropterus | Andaman Green-Pigeon | Treron chloropterus | pomgrp4 |
| Thick-billed Green Pigeon | Treron curvirostra | Thick-billed Green-Pigeon | Treron curvirostra | thbpig1 |
| Flores Green Pigeon | Treron floris | Flores Green-Pigeon | Treron floris | flgpig1 |
| Whistling Green Pigeon | Treron formosae | Whistling Green-Pigeon | Treron formosae | whgpig1 |
| Cinnamon-headed Green Pigeon | Treron fulvicollis | Cinnamon-headed Green-Pigeon | Treron fulvicollis | cihpig1 |
| Little Green Pigeon | Treron olax | Little Green-Pigeon | Treron olax | ligpig1 |
| Sumatran Green Pigeon | Treron oxyurus | Sumatran Green-Pigeon | Treron oxyurus | gnspig1 |
| Ashy-headed Green Pigeon | Treron phayrei | Ashy-headed Green-Pigeon | Treron phayrei | pomgrp5 |
| Yellow-footed Green Pigeon | Treron phoenicopterus | Yellow-footed Green-Pigeon | Treron phoenicopterus | yefpig1 |
| Sri Lanka Green Pigeon | Treron pompadora | Sri Lanka Green-Pigeon | Treron pompadora | pogpig1 |
| Yellow-vented Green Pigeon | Treron seimundi | Yellow-vented Green-Pigeon | Treron seimundi | yevpig1 |
| White-bellied Green Pigeon | Treron sieboldii | White-bellied Green-Pigeon | Treron sieboldii | whbpig1 |
| Wedge-tailed Green Pigeon | Treron sphenurus | Wedge-tailed Green-Pigeon | Treron sphenurus | wetpig1 |
| Pink-necked Green Pigeon | Treron vernans | Pink-necked Green-Pigeon | Treron vernans | pinpig3 |
| Bruce's Green Pigeon | Treron waalia | Bruce's Green-Pigeon | Treron waalia | brgpig1 |
| Christmas Island Thrush | Turdus erythropleurus | Christmas Island-Thrush | Turdus erythropleurus | islthr9 |
| Luzon Island Thrush | Turdus thomassoni | Luzon Island-Thrush | Turdus thomassoni | islthr36 |
| Black-billed Wood Dove | Turtur abyssinicus | Black-billed Wood-Dove | Turtur abyssinicus | bbwdov1 |
| Blue-spotted Wood Dove | Turtur afer | Blue-spotted Wood-Dove | Turtur afer | bswdov1 |
| Blue-headed Wood Dove | Turtur brehmeri | Blue-headed Wood-Dove | Turtur brehmeri | bhwdov1 |
| Emerald-spotted Wood Dove | Turtur chalcospilos | Emerald-spotted Wood-Dove | Turtur chalcospilos | eswdov1 |
| Karoo Scrub Robin | Tychaedon coryphoeus | Karoo Scrub-Robin | Tychaedon coryphoeus | kasrob2 |
| Greater Prairie Chicken | Tympanuchus cupido | Greater Prairie-Chicken | Tympanuchus cupido | grpchi |
| Lesser Prairie Chicken | Tympanuchus pallidicinctus | Lesser Prairie-Chicken | Tympanuchus pallidicinctus | lepchi |
| Andaman Masked Owl | Tyto deroepstorffi | Andaman Masked-Owl | Tyto deroepstorffi | barowl5 |
| Minahasa Masked Owl | Tyto inexspectata | Minahasa Masked-Owl | Tyto inexspectata | minowl1 |
| Red-cheeked Cordon-bleu | Uraeginthus bengalus | Red-cheeked Cordonbleu | Uraeginthus bengalus | reccor |
| Blue-capped Cordon-bleu | Uraeginthus cyanocephalus | Blue-capped Cordonbleu | Uraeginthus cyanocephalus | blccor1 |
| Long-tailed Ground Roller | Uratelornis chimaera | Long-tailed Ground-Roller | Uratelornis chimaera | ltgrol1 |
| Taiwan Blue Magpie | Urocissa caerulea | Taiwan Blue-Magpie | Urocissa caerulea | formag1 |
| Red-billed Blue Magpie | Urocissa erythroryncha | Red-billed Blue-Magpie | Urocissa erythroryncha | rbbmag |
| Yellow-billed Blue Magpie | Urocissa flavirostris | Yellow-billed Blue-Magpie | Urocissa flavirostris | gobmag1 |
| Sri Lanka Blue Magpie | Urocissa ornata | Sri Lanka Blue-Magpie | Urocissa ornata | ceymag1 |
| Sahel Paradise Whydah | Vidua orientalis | Sahel Paradise-Whydah | Vidua orientalis | nopwhy1 |
| Angola Cave Chat | Xenocopsychus ansorgei | Angola Cave-Chat | Xenocopsychus ansorgei | anccha1 |
| Amazonian Plain Xenops | Xenops genibarbis | Amazonian Plain-Xenops | Xenops genibarbis | plaxen3 |
| Northern Plain Xenops | Xenops mexicanus | Northern Plain-Xenops | Xenops mexicanus | plaxen2 |
| Atlantic Plain Xenops | Xenops minutus | Atlantic Plain-Xenops | Xenops minutus | plaxen4 |
| Baudin's Black Cockatoo | Zanda baudinii | Baudin's Black-Cockatoo | Zanda baudinii | whtblc1 |
| Yellow-tailed Black Cockatoo | Zanda funerea | Yellow-tailed Black-Cockatoo | Zanda funerea | ytbcoc1 |
| Carnaby's Black Cockatoo | Zanda latirostris | Carnaby's Black-Cockatoo | Zanda latirostris | slbblc1 |

### capitalization

| BirdNET common name | BirdNET scientific name | eBird common name / candidate | eBird scientific name | eBird code |
| --- | --- | --- | --- | --- |
| Cuckoo-finch | Anomalospiza imberbis | Cuckoo-Finch | Anomalospiza imberbis | parwea1 |
| African red-rumped swallow | Cecropis melanocrissus | African Red-rumped Swallow | Cecropis melanocrissus | rerswa12 |
| Magnificent Bird-of-paradise | Diphyllodes magnificus | Magnificent Bird-of-Paradise | Diphyllodes magnificus | mbopar2 |
| King Bird-of-paradise | Cicinnurus regius | King Bird-of-Paradise | Cicinnurus regius | kbopar1 |
| Wilson's Bird-of-paradise | Diphyllodes respublica | Wilson's Bird-of-Paradise | Diphyllodes respublica | wbopar1 |
| Rusty Mouse-warbler | Origma murina | Rusty Mouse-Warbler | Origma murina | rumwar1 |
| Mountain Mouse-warbler | Origma robusta | Mountain Mouse-Warbler | Origma robusta | momwar1 |
| Citrine Canary-flycatcher | Culicicapa helianthea | Citrine Canary-Flycatcher | Culicicapa helianthea | citcaf1 |
| Crab-plover | Dromas ardeola | Crab-Plover | Dromas ardeola | craplo1 |
| White-browed Tit-warbler | Leptopoecile sophiae | White-browed Tit-Warbler | Leptopoecile sophiae | wbtwar1 |
| South American Painted-snipe | Nycticryphes semicollaris | South American Painted-Snipe | Nycticryphes semicollaris | soapas1 |
| D'Orbigny's Chat-Tyrant | Ochthoeca oenanthoides | d'Orbigny's Chat-Tyrant | Ochthoeca oenanthoides | dorcht1 |
| Greater Bird-of-paradise | Paradisaea apoda | Greater Bird-of-Paradise | Paradisaea apoda | gbopar2 |
| Emperor Bird-of-paradise | Paradisaea guilielmi | Emperor Bird-of-Paradise | Paradisaea guilielmi | ebopar1 |
| Lesser Bird-of-paradise | Paradisaea minor | Lesser Bird-of-Paradise | Paradisaea minor | lbopar1 |
| Raggiana Bird-of-paradise | Paradisaea raggiana | Raggiana Bird-of-Paradise | Paradisaea raggiana | rbopar1 |
| Red Bird-of-paradise | Paradisaea rubra | Red Bird-of-Paradise | Paradisaea rubra | rbopar2 |
| Blue Bird-of-paradise | Paradisornis rudolphi | Blue Bird-of-Paradise | Paradisornis rudolphi | bbopar1 |
| Black-crowned Palm-tanager | Phaenicophilus palmarum | Black-crowned Palm-Tanager | Phaenicophilus palmarum | bcptan1 |
| Trilling Shrike-babbler | Pteruthius aenobarbus | Trilling Shrike-Babbler | Pteruthius aenobarbus | cfsbab1 |
| White-browed Shrike-babbler | Pteruthius aeralatus | White-browed Shrike-Babbler | Pteruthius aeralatus | whbshb1 |
| Pied Shrike-babbler | Pteruthius flaviscapis | Pied Shrike-Babbler | Pteruthius flaviscapis | wbsbab2 |
| Clicking Shrike-babbler | Pteruthius intermedius | Clicking Shrike-Babbler | Pteruthius intermedius | clishb1 |
| Black-eared Shrike-babbler | Pteruthius melanotis | Black-eared Shrike-Babbler | Pteruthius melanotis | besbab1 |
| Black-headed Shrike-babbler | Pteruthius rufiventer | Black-headed Shrike-Babbler | Pteruthius rufiventer | bhsbab1 |
| Green Shrike-babbler | Pteruthius xanthochlorus | Green Shrike-Babbler | Pteruthius xanthochlorus | grsbab1 |
| Rosy Thrush-tanager | Rhodinocichla rosea | Rosy Thrush-Tanager | Rhodinocichla rosea | rottan2 |
| Greater Painted-snipe | Rostratula benghalensis | Greater Painted-Snipe | Rostratula benghalensis | grpsni1 |
| Twelve-wired Bird-of-paradise | Seleucidis melanoleucus | Twelve-wired Bird-of-Paradise | Seleucidis melanoleucus | twwbop1 |
| Papuan island-thrush | Turdus papuensis | Papuan Island-Thrush | Turdus papuensis | papist1 |
| Fiji island-thrush | Turdus ruficeps | Fiji Island-Thrush | Turdus ruficeps | fijist1 |

### other_common_name_change

| BirdNET common name | BirdNET scientific name | eBird common name / candidate | eBird scientific name | eBird code |
| --- | --- | --- | --- | --- |
| Grey Thornbill | Acanthiza cinerea | Gray Thornbill | Acanthiza cinerea | mouger1 |
| New Guinea Thornbill | Acanthiza murina | Papuan Thornbill | Acanthiza murina | paptho1 |
| White-bellied Goshawk | Tachyspiza haplochroa | New Caledonian Goshawk | Tachyspiza haplochroa | necgos1 |
| Black Sparrowhawk | Astur melanoleucus | Black Goshawk | Astur melanoleucus | blagos1 |
| Grey Goshawk | Tachyspiza novaehollandiae | Gray Goshawk | Tachyspiza novaehollandiae | grygos1 |
| Grey-bellied Hawk | Accipiter poliogaster | Gray-bellied Hawk | Accipiter poliogaster | gybhaw1 |
| Spot-tailed Sparrowhawk | Tachyspiza trinotata | Spot-tailed Goshawk | Tachyspiza trinotata | sptgos1 |
| Cape Verde Warbler | Acrocephalus brevipennis | Cape Verde Swamp Warbler | Acrocephalus brevipennis | cvswar1 |
| Cook Reed Warbler | Acrocephalus kerearako | Cook Islands Reed Warbler | Acrocephalus kerearako | cirwar2 |
| Spotted Wood Kingfisher | Actenoides lindsayi | Spotted Kingfisher | Actenoides lindsayi | spokin1 |
| Bar-throated Minla | Actinodura strigula | Chestnut-tailed Minla | Actinodura strigula | chtmin1 |
| Black-throated Bushtit | Aegithalos concinnus | Black-throated Tit | Aegithalos concinnus | blttit2 |
| Pygmy Bushtit | Aegithalos exilis | Pygmy Tit | Aegithalos exilis | pygtit1 |
| Sooty Bushtit | Aegithalos fuliginosus | Sooty Tit | Aegithalos fuliginosus | sootit1 |
| Silver-throated Bushtit | Aegithalos glaucogularis | Silver-throated Tit | Aegithalos glaucogularis | lottit5 |
| Black-browed Bushtit | Aegithalos iouschistos | Black-browed Tit | Aegithalos iouschistos | bkbtit3 |
| White-throated Bushtit | Aegithalos niveogularis | White-throated Tit | Aegithalos niveogularis | whttit1 |
| Marshall's Iora | Aegithina nigrolutea | White-tailed Iora | Aegithina nigrolutea | whtior1 |
| Edible-nest Swiftlet | Aerodramus fuciphagus | White-nest Swiftlet | Aerodramus fuciphagus | y00731 |
| Caroline Swiftlet | Aerodramus inquietus | Caroline Islands Swiftlet | Aerodramus inquietus | caiswi1 |
| Grey-green Scrubwren | Aethomyias arfakianus | Gray-green Scrubwren | Aethomyias arfakianus | gygscr1 |
| Congo Peafowl | Afropavo congensis | Congo Peacock | Afropavo congensis | conpea1 |
| Southern Black Korhaan | Afrotis afra | Black Bustard | Afrotis afra | blabus3 |
| Northern Black Korhaan | Afrotis afraoides | White-quilled Bustard | Afrotis afraoides | whqbus1 |
| Grey-headed Lovebird | Agapornis canus | Gray-headed Lovebird | Agapornis canus | gyhlov1 |
| Greyish Baywing | Agelaioides badius | Grayish Baywing | Agelaioides badius | bawcow4 |
| Grey-bellied Shrike-Tyrant | Agriornis micropterus | Gray-bellied Shrike-Tyrant | Agriornis micropterus | gybsht1 |
| Malaysian Blue-banded Kingfisher | Alcedo peninsulae | Malayan Blue-banded Kingfisher | Alcedo peninsulae | bubkin1 |
| Grey-cheeked Fulvetta | Alcippe morrisonia | Morrison's Fulvetta | Alcippe morrisonia | gycful1 |
| Chukar Partridge | Alectoris chukar | Chukar | Alectoris chukar | chukar |
| Little Auk | Alle alle | Dovekie | Alle alle | doveki |
| Grey-cheeked Bulbul | Alophoixus tephrogenys | Gray-cheeked Bulbul | Alophoixus tephrogenys | gycbul2 |
| Palawan Bulbul | Alophoixus frater | Gray-throated Bulbul | Alophoixus frater | gytbul1 |
| Orange-breasted Waxbill | Amandava subflava | Zebra Waxbill | Amandava subflava | zebwax2 |
| Plain Bush-hen | Amaurornis olivacea | Philippine Bush-hen | Amaurornis olivacea | plabuh1 |
| Yucatan Amazon | Amazona xantholora | Yellow-lored Amazon | Amazona xantholora | yelpar1 |
| Thick-billed Weaver | Amblyospiza albifrons | Grosbeak Weaver | Amblyospiza albifrons | growea1 |
| Grey-bellied Antbird | Ammonastes pelzelni | Gray-bellied Antbird | Ammonastes pelzelni | gybant1 |
| Grey-headed Antbird | Ampelornis griseiceps | Gray-headed Antbird | Ampelornis griseiceps | gyhant1 |
| Grey Grasswren | Amytornis barbatus | Gray Grasswren | Amytornis barbatus | grygra1 |
| Bamboo Foliage-gleaner | Anabazenops dorsalis | Dusky-cheeked Foliage-gleaner | Anabazenops dorsalis | ducfog1 |
| New Zealand Plover | Anarhynchus obscurus | Red-breasted Dotterel | Anarhynchus obscurus | rebdot1 |
| Grey Teal | Anas gracilis | Gray Teal | Anas gracilis | gretea1 |
| Campbell Teal | Anas nesiotis | Campbell Islands Teal | Anas nesiotis | caitea1 |
| Grey-breasted Mountain Toucan | Andigena hypoglauca | Gray-breasted Mountain-Toucan | Andigena hypoglauca | gybmot1 |
| Santa Marta Mountain Tanager | Anisognathus melanogenys | Black-cheeked Mountain Tanager | Anisognathus melanogenys | bkcmot1 |
| Lear's Macaw | Anodorhynchus leari | Indigo Macaw | Anodorhynchus leari | indmac1 |
| Austen's Brown Hornbill | Anorrhinus austeni | Brown Hornbill | Anorrhinus austeni | brnhor1 |
| Tickell's Brown Hornbill | Anorrhinus tickelli | Rusty-cheeked Hornbill | Anorrhinus tickelli | ruchor1 |
| Greylag Goose | Anser anser | Graylag Goose | Anser anser | gragoo |
| Grey Penduline Tit | Anthoscopus caroli | African Penduline-Tit | Anthoscopus caroli | afptit1 |
| Mangrove Sunbird | Anthreptes gabonicus | Mouse-brown Sunbird | Anthreptes gabonicus | mobsun1 |
| Grey-chinned Sunbird | Anthreptes tephrolaemus | Gray-chinned Sunbird | Anthreptes tephrolaemus | grnsun2 |
| Bushveld Pipit | Anthus caffer | Bush Pipit | Anthus caffer | buspip1 |
| African Rock Pipit | Anthus crenatus | Yellow-tufted Pipit | Anthus crenatus | yetpip1 |
| Wood Pipit | Anthus nyassae | Woodland Pipit | Anthus nyassae | woopip1 |
| European Rock Pipit | Anthus petrosus | Rock Pipit | Anthus petrosus | rocpip1 |
| Lowland Masked Apalis | Apalis binotata | Masked Apalis | Apalis binotata | masapa1 |
| Grey Apalis | Apalis cinerea | Gray Apalis | Apalis cinerea | gryapa1 |
| Mountain Masked Apalis | Apalis personata | Black-faced Apalis | Apalis personata | blfapa1 |
| Okarito Kiwi | Apteryx rowi | Okarito Brown Kiwi | Apteryx rowi | okbkiw1 |
| Malagasy Black Swift | Apus balstoni | Malagasy Swift | Apus balstoni | madswi1 |
| African Black Swift | Apus barbatus | African Swift | Apus barbatus | afrswi1 |
| Fork-tailed Swift | Apus pacificus | Pacific Swift | Apus pacificus | fotswi |
| Grey-breasted Spiderhunter | Arachnothera modesta | Gray-breasted Spiderhunter | Arachnothera modesta | gybspi2 |
| Grey-cowled Wood Rail | Aramides cajaneus | Gray-cowled Wood-Rail | Aramides cajaneus | gycwor1 |
| Caatinga Parakeet | Eupsittula cactorum | Cactus Parakeet | Eupsittula cactorum | cacpar1 |
| Finsch's Parakeet | Psittacara finschi | Crimson-fronted Parakeet | Psittacara finschi | crfpar |
| Malayan Partridge | Arborophila campbelli | Malaysian Partridge | Arborophila campbelli | gybpar3 |
| Grey Heron | Ardea cinerea | Gray Heron | Ardea cinerea | graher1 |
| White-necked Heron | Ardea pacifica | Pacific Heron | Ardea pacifica | pacher1 |
| Large Grey Babbler | Argya malcolmi | Large Gray Babbler | Argya malcolmi | lagbab2 |
| Maranon Sparrow | Arremon nigriceps | Marañon Sparrow | Arremon nigriceps | bkcspa2 |
| Grey-browed Brushfinch | Arremon assimilis | Gray-browed Brushfinch | Arremon assimilis | sthbrf8 |
| Princess Stephanie's Astrapia | Astrapia stephaniae | Stephanie's Astrapia | Astrapia stephaniae | prsast1 |
| Grey-eared Brushfinch | Atlapetes melanolaemus | Black-faced Brushfinch | Atlapetes melanolaemus | bkfbrf1 |
| Slaty Brushfinch | Atlapetes schistaceus | Northern Slaty Brushfinch | Atlapetes schistaceus | slabru1 |
| Taczanowski's Brushfinch | Atlapetes taczanowskii | Peruvian Slaty Brushfinch | Atlapetes taczanowskii | slabru2 |
| Tricolored Brushfinch | Atlapetes tricolor | Golden-crowned Brushfinch | Atlapetes tricolor | tribrf2 |
| White-eyed Attila | Attila bolivianus | Dull-capped Attila | Attila bolivianus | ducatt1 |
| Grey-hooded Attila | Attila rufus | Gray-hooded Attila | Attila rufus | gyhatt1 |
| Tepui Foliage-gleaner | Syndactyla roraimae | White-throated Foliage-gleaner | Syndactyla roraimae | wtfgle1 |
| Grey Crowned Crane | Balearica regulorum | Gray Crowned-Crane | Balearica regulorum | grccra1 |
| Black-eared Warbler | Basileuterus melanotis | Costa Rican Warbler | Basileuterus melanotis | thswar5 |
| Grey-headed Batis | Batis orientalis | Gray-headed Batis | Batis orientalis | gyhbat1 |
| Grey-headed Bristlebill | Bleda canicapillus | Gray-headed Bristlebill | Bleda canicapillus | gyhbri1 |
| African Grey Flycatcher | Bradornis microrhynchus | African Gray Flycatcher | Bradornis microrhynchus | afgfly1 |
| Bangwa Forest Warbler | Bradypterus bangwaensis | Bangwa Warbler | Bradypterus bangwaensis | banscw1 |
| Dja River Scrub Warbler | Bradypterus grandis | Dja River Swamp Warbler | Bradypterus grandis | jrswar1 |
| Grey Emutail | Bradypterus seebohmi | Gray Emutail | Bradypterus seebohmi | gryemt1 |
| Brant Goose | Branta bernicla | Brant | Branta bernicla | brant |
| Nene | Branta sandvicensis | Hawaiian Goose | Branta sandvicensis | hawgoo |
| Grey-cheeked Parakeet | Brotogeris pyrrhoptera | Gray-cheeked Parakeet | Brotogeris pyrrhoptera | gycpar1 |
| Indian Eagle-Owl | Bubo bengalensis | Rock Eagle-Owl | Bubo bengalensis | roeowl1 |
| Greyish Eagle-Owl | Bubo cinerascens | Grayish Eagle-Owl | Bubo cinerascens | graeao1 |
| Lesser Horned Owl | Bubo magellanicus | Magellanic Horned Owl | Bubo magellanicus | grhowl2 |
| Buff-banded Thicketbird | Cincloramphus bivittatus | Buff-banded Bushbird | Cincloramphus bivittatus | bubbus1 |
| Bush Stone-curlew | Burhinus grallarius | Bush Thick-knee | Burhinus grallarius | butkne1 |
| Indian Stone-curlew | Burhinus indicus | Indian Thick-knee | Burhinus indicus | indthk1 |
| Eurasian Stone-curlew | Burhinus oedicnemus | Eurasian Thick-knee | Burhinus oedicnemus | eutkne1 |
| Grey-faced Buzzard | Butastur indicus | Gray-faced Buzzard | Butastur indicus | gyfbuz1 |
| Rough-legged Buzzard | Buteo lagopus | Rough-legged Hawk | Buteo lagopus | rolhaw |
| Grey-lined Hawk | Buteo nitidus | Gray-lined Hawk | Buteo nitidus | gryhaw3 |
| Grey Hawk | Buteo plagiatus | Gray Hawk | Buteo plagiatus | gryhaw2 |
| Red-vented Cockatoo | Cacatua haematuropygia | Philippine Cockatoo | Cacatua haematuropygia | phicoc1 |
| Mexican Cacique | Cassiculus melanicterus | Yellow-winged Cacique | Cassiculus melanicterus | yewcac1 |
| Solitary Cacique | Cacicus solitarius | Solitary Black Cacique | Cacicus solitarius | sobcac1 |
| Grey-bellied Cuckoo | Cacomantis passerinus | Gray-bellied Cuckoo | Cacomantis passerinus | placuc3 |
| Grey Wren-Warbler | Calamonastes simplex | Gray Wren-Warbler | Calamonastes simplex | grywrw1 |
| Hume's Short-toed Lark | Calandrella acutirostris | Hume's Lark | Calandrella acutirostris | humlar1 |
| Brown Barbet | Caloramphus fuliginosus | Bornean Brown Barbet | Caloramphus fuliginosus | brnbar2 |
| Sooty Barbet | Caloramphus hayii | Malayan Brown Barbet | Caloramphus hayii | soobar2 |
| Lucifer Sheartail | Calothorax lucifer | Lucifer Hummingbird | Calothorax lucifer | luchum |
| Beautiful Sheartail | Calothorax pulcher | Beautiful Hummingbird | Calothorax pulcher | beahum1 |
| Bleating Camaroptera | Camaroptera brachyura | Green-backed Camaroptera | Camaroptera brachyura | grbcam1 |
| Southern Beardless Tyrannulet | Camptostoma obsoletum | Southeastern Beardless-Tyrannulet | Camptostoma obsoletum | soubet2 |
| Grey-breasted Sabrewing | Campylopterus largipennis | Gray-breasted Sabrewing | Campylopterus largipennis | gybsab1 |
| Grey-barred Wren | Campylorhynchus megalopterus | Gray-barred Wren | Campylorhynchus megalopterus | grbwre1 |
| Grey Wren | Cantorchilus griseus | Gray Wren | Cantorchilus griseus | grywre1 |
| European Nightjar | Caprimulgus europaeus | Eurasian Nightjar | Caprimulgus europaeus | eurnig1 |
| Grey Nightjar | Caprimulgus jotaka | Gray Nightjar | Caprimulgus jotaka | grynig1 |
| Grey-crowned Goldfinch | Carduelis caniceps | Gray-crowned Goldfinch | Carduelis caniceps | eurgol2 |
| Common Linnet | Linaria cannabina | Eurasian Linnet | Linaria cannabina | eurlin1 |
| Grey-cheeked Thrush | Catharus minimus | Gray-cheeked Thrush | Catharus minimus | gycthr |
| Grey Cuckooshrike | Ceblepyris caesius | Gray Cuckooshrike | Ceblepyris caesius | grycus1 |
| Red-breasted Swallow | Cecropis semirufa | Rufous-chested Swallow | Cecropis semirufa | rucswa2 |
| Gunnison Grouse | Centrocercus minimus | Gunnison Sage-Grouse | Centrocercus minimus | gusgro |
| Sage Grouse | Centrocercus urophasianus | Greater Sage-Grouse | Centrocercus urophasianus | saggro |
| White-necked Coucal | Centropus ateralbus | Pied Coucal | Centropus ateralbus | piecou1 |
| Grey Antbird | Cercomacra cinerascens | Gray Antbird | Cercomacra cinerascens | gryant2 |
| Grey Warbler-Finch | Certhidea fusca | Gray Warbler-Finch | Certhidea fusca | grywaf1 |
| Yellow-bellied Bush Warbler | Horornis acanthizoides | Yellowish-bellied Bush Warbler | Horornis acanthizoides | ybbwar1 |
| Grey-sided Bush Warbler | Cettia brunnifrons | Gray-sided Bush Warbler | Cettia brunnifrons | gysbuw1 |
| Grey-rumped Swift | Chaetura cinereiventris | Gray-rumped Swift | Chaetura cinereiventris | grrswi1 |
| Common Emerald Dove | Chalcophaps indica | Asian Emerald Dove | Chalcophaps indica | emedov2 |
| Stephan's Emerald Dove | Chalcophaps stephani | Stephan's Dove | Chalcophaps stephani | stedov1 |
| Cryptic Antthrush | Chamaeza meruloides | Such's Antthrush | Chamaeza meruloides | sucant1 |
| Yellow-bellied Fantail | Chelidorhynx hypoxanthus | Yellow-bellied Fairy-Fantail | Chelidorhynx hypoxanthus | yebfan1 |
| Blue Manakin | Chiroxiphia caudata | Swallow-tailed Manakin | Chiroxiphia caudata | swtman1 |
| Blue-throated Sapphire | Chlorestes eliciae | Blue-throated Goldentail | Chlorestes eliciae | bltgol1 |
| Falkenstein's Greenbul | Chlorocichla falkensteini | Yellow-necked Greenbul | Chlorocichla falkensteini | yengre1 |
| Bocage's Bushshrike | Chlorophoneus bocagei | Gray-green Bushshrike | Chlorophoneus bocagei | gygbus1 |
| Orange-breasted Bushshrike | Chlorophoneus sulfureopectus | Sulphur-breasted Bushshrike | Chlorophoneus sulfureopectus | subbus1 |
| Yellow-crested Woodpecker | Chloropicus xantholophus | Golden-crowned Woodpecker | Chloropicus xantholophus | gocwoo3 |
| Yellow-whiskered Chlorospingus | Chlorospingus parvirostris | Short-billed Chlorospingus | Chlorospingus parvirostris | shbbut1 |
| Grey-headed Gull | Chroicocephalus cirrocephalus | Gray-hooded Gull | Chroicocephalus cirrocephalus | grhgul |
| Grey Trembler | Cinclocerthia gutturalis | Gray Trembler | Cinclocerthia gutturalis | gratre1 |
| Chilean Seaside Cinclodes | Cinclodes nigrofumosus | Seaside Cinclodes | Cinclodes nigrofumosus | seacin1 |
| Grey-flanked Cinclodes | Cinclodes oustaleti | Gray-flanked Cinclodes | Cinclodes oustaleti | gyfcin1 |
| Peruvian Seaside Cinclodes | Cinclodes taczanowskii | Surf Cinclodes | Cinclodes taczanowskii | surcin1 |
| Sepia-brown Wren | Cinnycerthia olivascens | Sharpe's Wren | Cinnycerthia olivascens | shawre1 |
| Malagasy Green Sunbird | Cinnyris notatus | Malagasy Sunbird | Cinnyris notatus | madsun1 |
| Congo Serpent Eagle | Circaetus spectabilis | Congo Snake-Eagle | Circaetus spectabilis | coseag1 |
| Long-tailed Cisticola | Cisticola angusticauda | Tabora Cisticola | Cisticola angusticauda | tabcis1 |
| Short-winged Cisticola | Cisticola brachypterus | Siffling Cisticola | Cisticola brachypterus | sifcis1 |
| Neddicky | Cisticola fulvicapilla | Piping Cisticola | Cisticola fulvicapilla | pipcis2 |
| Grey-backed Cisticola | Cisticola subruficapilla | Gray-backed Cisticola | Cisticola subruficapilla | rehcis2 |
| Marsh Wren | Cistothorus palustris | Eastern Marsh Wren | Cistothorus palustris | eamwre1 |
| Jacobin Cuckoo | Clamator jacobinus | Pied Cuckoo | Clamator jacobinus | piecuc1 |
| Henna-capped Foliage-gleaner | Clibanornis rectirostris | Chestnut-capped Foliage-gleaner | Clibanornis rectirostris | ccfgle1 |
| Grey-hooded Bush Tanager | Cnemoscopus rubrirostris | Pink-billed Cnemoscopus | Cnemoscopus rubrirostris | gyhbut2 |
| Grey-capped Cuckoo | Coccyzus lansbergi | Gray-capped Cuckoo | Coccyzus lansbergi | gyccuc |
| Grey-crowned Woodpecker | Colaptes auricularis | Gray-crowned Woodpecker | Colaptes auricularis | grcwoo1 |
| Yucatan Bobwhite | Colinus nigrogularis | Black-throated Bobwhite | Colinus nigrogularis | bltbob1 |
| Grey Shrikethrush | Colluricincla harmonica | Gray Shrikethrush | Colluricincla harmonica | grysht1 |
| Western Jackdaw | Coloeus monedula | Eurasian Jackdaw | Coloeus monedula | eurjac |
| African Olive Pigeon | Columba arquatrix | Rameron Pigeon | Columba arquatrix | rampig1 |
| Rock Dove | Columba livia | Rock Pigeon | Columba livia | rocpig |
| Island Bronze-naped Pigeon | Columba malherbii | Sao Tome Pigeon | Columba malherbii | satpig1 |
| Grey Honeyeater | Conopophila whitei | Gray Honeyeater | Conopophila whitei | gryhon1 |
| Black-shouldered Cicadabird | Edolisoma incertum | Papuan Cicadabird | Edolisoma incertum | papcus1 |
| Malayan Cuckooshrike | Coracina larutensis | Malaysian Cuckooshrike | Coracina larutensis | larcuc3 |
| Black-bellied Cuckooshrike | Edolisoma montanum | Black-bellied Cicadabird | Edolisoma montanum | bkbcus2 |
| Grey-headed Cuckooshrike | Edolisoma schisticeps | Gray-headed Cicadabird | Edolisoma schisticeps | gyhcus1 |
| Seychelles Black Parrot | Coracopsis barklyi | Seychelles Parrot | Coracopsis barklyi | seypar1 |
| Northern Raven | Corvus corax | Common Raven | Corvus corax | comrav |
| Grey Crow | Corvus tristis | Gray Crow | Corvus tristis | grycro1 |
| White-billed Crow | Corvus woodfordi | Guadalcanal Crow | Corvus woodfordi | guacro1 |
| Red Pileated Finch | Coryphospingus cucullatus | Red-crested Finch | Coryphospingus cucullatus | recfin1 |
| Grey Pileated Finch | Coryphospingus pileatus | Pileated Finch | Coryphospingus pileatus | pilfin1 |
| Grey Go-away-bird | Crinifer concolor | Gray Go-away-bird | Crinifer concolor | grygab1 |
| Olive-flanked Ground Robin | Dessonornis anomalus | Olive-flanked Robin-Chat | Dessonornis anomalus | ofrcha1 |
| Archer's Ground Robin | Dessonornis archeri | Archer's Robin-Chat | Dessonornis archeri | arrcha1 |
| Grey-winged Robin-Chat | Sheppardia polioptera | Gray-winged Robin-Chat | Sheppardia polioptera | gywroc1 |
| Grey Butcherbird | Cracticus torquatus | Gray Butcherbird | Cracticus torquatus | grybut1 |
| Grey-headed Spinetail | Cranioleuca semicinerea | Gray-headed Spinetail | Cranioleuca semicinerea | gyhspi1 |
| Yellow-throated Seedeater | Crithagra flavigula | Yellow-throated Serin | Crithagra flavigula | yetser1 |
| Salvadori's Seedeater | Crithagra xantholaema | Salvadori's Serin | Crithagra xantholaema | salser1 |
| Grey-crowned Crocias | Laniellus langbianis | Gray-crowned Crocias | Laniellus langbianis | gyccro1 |
| Grey-legged Tinamou | Crypturellus duidae | Gray-legged Tinamou | Crypturellus duidae | gyltin1 |
| Malaysian Hawk-Cuckoo | Hierococcyx fugax | Malayan Hawk-Cuckoo | Hierococcyx fugax | malhac1 |
| Dark Hawk-Cuckoo | Hierococcyx bocki | Bock's Hawk-Cuckoo | Hierococcyx bocki | larhac1 |
| Grey-headed Canary-flycatcher | Culicicapa ceylonensis | Gray-headed Canary-Flycatcher | Culicicapa ceylonensis | gyhcaf1 |
| Sharp-tailed Grass Tyrant | Culicivora caudacuta | Sharp-tailed Tyrant | Culicivora caudacuta | shttyr1 |
| Common Whitethroat | Curruca communis | Greater Whitethroat | Curruca communis | grewhi1 |
| Burrowing Parrot | Cyanoliseus patagonus | Burrowing Parakeet | Cyanoliseus patagonus | burpar |
| Grey Sunbird | Cyanomitra veroxii | Mouse-colored Sunbird | Cyanomitra veroxii | mocsun2 |
| Yellow-crowned Parakeet | Cyanoramphus auriceps | Yellow-crowned Kakariki | Cyanoramphus auriceps | yefpar3 |
| Norfolk Parakeet | Cyanoramphus cookii | Norfolk Island Kakariki | Cyanoramphus cookii | noipar1 |
| Chatham Islands Parakeet | Cyanoramphus forbesi | Chatham Islands Kakariki | Cyanoramphus forbesi | chipar1 |
| Malherbe's Parakeet | Cyanoramphus malherbi | Orange-fronted Kakariki | Cyanoramphus malherbi | malpar2 |
| Red-crowned Parakeet | Cyanoramphus novaezelandiae | Red-crowned Kakariki | Cyanoramphus novaezelandiae | refpar4 |
| New Caledonian Parakeet | Cyanoramphus saisseti | New Caledonian Kakariki | Cyanoramphus saisseti | necpar1 |
| Blue-fronted Blue Flycatcher | Eumyias hoevelli | Blue-fronted Flycatcher | Eumyias hoevelli | blffly1 |
| Matinan Blue Flycatcher | Eumyias sanfordi | Matinan Flycatcher | Eumyias sanfordi | matfly2 |
| Malaysian Blue Flycatcher | Cyornis turcosus | Malayan Blue Flycatcher | Cyornis turcosus | mabfly1 |
| Grey-chested Jungle Flycatcher | Cyornis umbratilis | Gray-chested Jungle Flycatcher | Cyornis umbratilis | gycjuf1 |
| American Black Swift | Cypseloides niger | Black Swift | Cypseloides niger | blkswi |
| Rough-crested Malkoha | Dasylophus superciliosus | Red-crested Malkoha | Dasylophus superciliosus | recmal1 |
| Grey-headed Sunbird | Deleornis axillaris | Gray-headed Sunbird | Deleornis axillaris | gyhsun1 |
| Grey Treepie | Dendrocitta formosae | Gray Treepie | Dendrocitta formosae | grytre1 |
| African Grey Woodpecker | Dendropicos goertae | African Gray Woodpecker | Dendropicos goertae | grywoo1 |
| Eastern Grey Woodpecker | Dendropicos spodocephalus | Mountain Gray Woodpecker | Dendropicos spodocephalus | gyhwoo1 |
| Grey-sided Flowerpecker | Dicaeum celebicum | Gray-sided Flowerpecker | Dicaeum celebicum | gysflo1 |
| Grey-bellied Flowerpiercer | Diglossa carbonaria | Gray-bellied Flowerpiercer | Diglossa carbonaria | gybflo1 |
| Masked Flowerpiercer | Diglossa cyanea | Warbling Masked Flowerpiercer | Diglossa cyanea | masflo7 |
| Golden-eyed Flowerpiercer | Diglossa glauca | Deep-blue Flowerpiercer | Diglossa glauca | debflo1 |
| Goliath Imperial Pigeon | Ducula goliath | New Caledonian Imperial-Pigeon | Ducula goliath | ncipig1 |
| Grey Imperial Pigeon | Ducula pickeringii | Gray Imperial-Pigeon | Ducula pickeringii | gryimp1 |
| Christmas Imperial Pigeon | Ducula whartoni | Christmas Island Imperial-Pigeon | Ducula whartoni | ciipig1 |
| Grey Catbird | Dumetella carolinensis | Gray Catbird | Dumetella carolinensis | grycat |
| Grey-necked Bunting | Emberiza buchanani | Gray-necked Bunting | Emberiza buchanani | gyhbun1 |
| Serra Finch | Embernagra longicauda | Pale-throated Pampa-Finch | Embernagra longicauda | ptpfin1 |
| Pampa Finch | Embernagra platensis | Great Pampa-Finch | Embernagra platensis | grpfin1 |
| Grey-capped Warbler | Eminia lepida | Gray-capped Warbler | Eminia lepida | gycwar3 |
| American Dusky Flycatcher | Empidonax oberholseri | Dusky Flycatcher | Empidonax oberholseri | dusfly |
| American Grey Flycatcher | Empidonax wrightii | Gray Flycatcher | Empidonax wrightii | gryfly |
| White-crowned Forktail | Enicurus leschenaulti | Javan Forktail | Enicurus leschenaulti | whcfor5 |
| Fiery-browed Starling | Enodes erythrophris | Fiery-browed Myna | Enodes erythrophris | fibmyn1 |
| Grey-backed Sparrow-Lark | Eremopterix verticalis | Gray-backed Sparrow-Lark | Eremopterix verticalis | gybspl1 |
| Little Yellow Flycatcher | Erythrocercus holochlorus | Yellow Flycatcher | Erythrocercus holochlorus | yelfly2 |
| Grey-sided Scimitar Babbler | Erythrogenys swinhoei | Gray-sided Scimitar-Babbler | Erythrogenys swinhoei | gysscb1 |
| Beach Stone-curlew | Esacus magnirostris | Beach Thick-knee | Esacus magnirostris | beathk1 |
| Great Stone-curlew | Esacus recurvirostris | Great Thick-knee | Esacus recurvirostris | grtkne1 |
| Grey Waxbill | Glaucestrilda perreini | Black-tailed Waxbill | Glaucestrilda perreini | bltwax1 |
| Grey-headed Tanager | Eucometis penicillata | Gray-headed Tanager | Eucometis penicillata | grhtan1 |
| American White Ibis | Eudocimus albus | White Ibis | Eudocimus albus | whiibi |
| Oaxaca Hummingbird | Eupherusa cyanophrys | Blue-capped Hummingbird | Eupherusa cyanophrys | blchum2 |
| Green-chinned Euphonia | Euphonia chalybea | Green-throated Euphonia | Euphonia chalybea | gnteup1 |
| White-lored Euphonia | Euphonia chrysopasta | Golden-bellied Euphonia | Euphonia chrysopasta | gobeup1 |
| Black-winged Red Bishop | Euplectes hordeaceus | Black-winged Bishop | Euplectes hordeaceus | blwbis1 |
| Blue Korhaan | Eupodotis caerulescens | Blue Bustard | Eupodotis caerulescens | blubus1 |
| Red-crested Korhaan | Lophotis ruficrista | Red-crested Bustard | Lophotis ruficrista | recbus1 |
| Karoo Korhaan | Heterotetrax vigorsii | Karoo Bustard | Heterotetrax vigorsii | karbus1 |
| Little Grey Greenbul | Eurillas gracilis | Gray Greenbul | Eurillas gracilis | grygre1 |
| Satanic Nightjar | Eurostopodus diabolicus | Diabolical Nightjar | Eurostopodus diabolicus | dianig1 |
| King Quail | Synoicus chinensis | Blue-breasted Quail | Synoicus chinensis | blbqua1 |
| Grey Kestrel | Falco ardosiaceus | Gray Kestrel | Falco ardosiaceus | grykes1 |
| Grey Falcon | Falco hypoleucos | Gray Falcon | Falco hypoleucos | gryfal1 |
| Common Kestrel | Falco tinnunculus | Eurasian Kestrel | Falco tinnunculus | eurkes |
| Atlas Pied Flycatcher | Ficedula speculigera | Atlas Flycatcher | Ficedula speculigera | atlfly1 |
| Black-headed Antthrush | Formicarius nigricapillus | Black-capped Antthrush | Formicarius nigricapillus | bkhant7 |
| Polynesian Wattled Honeyeater | Foulehaio carunculatus | Eastern Wattled-Honeyeater | Foulehaio carunculatus | easwah1 |
| Kikau | Foulehaio procerior | Western Wattled-Honeyeater | Foulehaio procerior | weswah1 |
| Fiji Wattled Honeyeater | Foulehaio taviunensis | Northern Wattled-Honeyeater | Foulehaio taviunensis | norwah1 |
| Grey-throated Tit-Flycatcher | Fraseria griseigularis | Gray-throated Tit-Flycatcher | Fraseria griseigularis | gyttif1 |
| Fraser's Forest Flycatcher | Fraseria ocreata | African Forest-Flycatcher | Fraseria ocreata | afffly1 |
| Grey Tit-Flycatcher | Fraseria plumbea | Gray Tit-Flycatcher | Fraseria plumbea | grytif1 |
| Eurasian Chaffinch | Fringilla coelebs | Common Chaffinch | Fringilla coelebs | comcha |
| Andean Coot | Fulica ardesiaca | Slate-colored Coot | Fulica ardesiaca | slccoo1 |
| Grey-hooded Fulvetta | Fulvetta cinereiceps | Gray-hooded Fulvetta | Fulvetta cinereiceps | sttful1 |
| Band-tailed Hornero | Furnarius figulus | Wing-banded Hornero | Furnarius figulus | wibhor1 |
| Bay Hornero | Furnarius torridus | Pale-billed Hornero | Furnarius torridus | pabhor2 |
| Blue-necked Jacamar | Galbula cyanicollis | Blue-cheeked Jacamar | Galbula cyanicollis | bucjac1 |
| Sykes's Lark | Galerida deva | Tawny Lark | Galerida deva | tawlar1 |
| Common Moorhen | Gallinula chloropus | Eurasian Moorhen | Gallinula chloropus | commoo3 |
| Lord Howe Woodhen | Gallirallus sylvestris | Lord Howe Rail | Gallirallus sylvestris | lohrai1 |
| Grey Junglefowl | Gallus sonneratii | Gray Junglefowl | Gallus sonneratii | grejun2 |
| Grey-sided Laughingthrush | Pterorhinus caerulatus | Gray-sided Laughingthrush | Pterorhinus caerulatus | gyslau |
| Grey Laughingthrush | Garrulax maesi | Gray Laughingthrush | Garrulax maesi | grylau1 |
| Black-throated Loon | Gavia arctica | Arctic Loon | Gavia arctica | arcloo |
| Song Parrot | Geoffroyus heteroclitus | Singing Parrot | Geoffroyus heteroclitus | sinpar1 |
| Orange-sided Thrush | Geokichla peronii | Orange-banded Thrush | Geokichla peronii | orbthr1 |
| Greyish Miner | Geositta maritima | Grayish Miner | Geositta maritima | gramin1 |
| Espanola Cactus Finch | Geospiza conirostris | Española Ground-Finch | Geospiza conirostris | larcaf2 |
| Grey-crowned Yellowthroat | Geothlypis poliocephala | Gray-crowned Yellowthroat | Geothlypis poliocephala | gycyel |
| Grey-fronted Quail-Dove | Geotrygon caniceps | Gray-fronted Quail-Dove | Geotrygon caniceps | gfqdov |
| Grey Gerygone | Gerygone igata | Gray Gerygone | Gerygone igata | gryger1 |
| Norfolk Gerygone | Gerygone modesta | Norfolk Island Gerygone | Gerygone modesta | noiger1 |
| East Brazilian Pygmy Owl | Glaucidium minutissimum | Least Pygmy-Owl | Glaucidium minutissimum | leapyo1 |
| Pacific Pygmy Owl | Glaucidium peruanum | Peruvian Pygmy-Owl | Glaucidium peruanum | pepowl1 |
| Sjöstedt's Barred Owlet | Glaucidium sjostedti | Sjöstedt's Owlet | Glaucidium sjostedti | sjoowl1 |
| Sri Lanka Hill Myna | Gracula ptilogenys | Sri Lanka Myna | Gracula ptilogenys | ceymyn1 |
| Indian Pied Myna | Gracupica contra | Indian Pied Starling | Gracupica contra | aspsta2 |
| Siamese Pied Myna | Gracupica floweri | Siamese Pied Starling | Gracupica floweri | aspsta7 |
| Grey-naped Antpitta | Grallaria griseonucha | Gray-naped Antpitta | Grallaria griseonucha | gynant1 |
| Rufous-breasted Antpitta | Grallaricula leymebambae | Leymebamba Antpitta | Grallaricula leymebambae | rubant7 |
| Slaty-crowned Antpitta | Grallaricula nana | Slate-crowned Antpitta | Grallaricula nana | slcant2 |
| Grey-throated Chat | Granatellus sallaei | Gray-throated Chat | Granatellus sallaei | grtcha1 |
| Grey-throated Barbet | Gymnobucco bonapartei | Gray-throated Barbet | Gymnobucco bonapartei | gytbar1 |
| Griffon Vulture | Gyps fulvus | Eurasian Griffon | Gyps fulvus | eurgri1 |
| Himalayan Vulture | Gyps himalayensis | Himalayan Griffon | Gyps himalayensis | himgri1 |
| Rüppell's Vulture | Gyps rueppelli | Rüppell's Griffon | Gyps rueppelli | ruegri1 |
| Grey-headed Kingfisher | Halcyon leucocephala | Gray-headed Kingfisher | Halcyon leucocephala | gyhkin1 |
| Fuertes's Parrot | Hapalopsittaca fuertesi | Indigo-winged Parrot | Hapalopsittaca fuertesi | inwpar1 |
| Papuan Eagle | Harpyopsis novaeguineae | New Guinea Eagle | Harpyopsis novaeguineae | negeag1 |
| Thick-billed Heleia | Heleia crassirostris | Flores Heleia | Heleia crassirostris | flowhe1 |
| Crested Heleia | Heleia dohertyi | Dark-crowned Heleia | Heleia dohertyi | dacwhe1 |
| Flame-throated Sunangel | Heliangelus micraster | Little Sunangel | Heliangelus micraster | litsun1 |
| Styan's Grasshopper Warbler | Helopsaltes pleskei | Pleske's Grasshopper Warbler | Helopsaltes pleskei | plewar1 |
| Grey-and-buff Woodpecker | Hemicircus concretus | Gray-and-buff Woodpecker | Hemicircus concretus | gabwoo3 |
| Grey-rumped Treeswift | Hemiprocne longipennis | Gray-rumped Treeswift | Hemiprocne longipennis | gyrtre1 |
| Drab-breasted Bamboo Tyrant | Hemitriccus diops | Drab-breasted Pygmy-Tyrant | Hemitriccus diops | drbpyt1 |
| Flammulated Bamboo Tyrant | Hemitriccus flammulatus | Flammulated Pygmy-Tyrant | Hemitriccus flammulatus | flapyt1 |
| Fork-tailed Tody-Tyrant | Hemitriccus furcatus | Fork-tailed Pygmy-Tyrant | Hemitriccus furcatus | fotpyt1 |
| Brown-breasted Bamboo Tyrant | Hemitriccus obsoletus | Brown-breasted Pygmy-Tyrant | Hemitriccus obsoletus | bnbpyt1 |
| Grey-breasted Wood Wren | Henicorhina leucophrys | Gray-breasted Wood-Wren | Henicorhina leucophrys | gbwwre1 |
| Orange-crested Manakin | Heterocercus aurantiivertex | Orange-crowned Manakin | Heterocercus aurantiivertex | orcman3 |
| Yellow-crested Manakin | Heterocercus flavivertex | Yellow-crowned Manakin | Heterocercus flavivertex | yecman2 |
| Flame-crested Manakin | Heterocercus linteatus | Flame-crowned Manakin | Heterocercus linteatus | flcman2 |
| Archer's Lark | Heteromirafra archeri | Liben Lark | Heteromirafra archeri | liblar1 |
| Ashy Robin | Heteromyias albispecularis | Arfak Robin | Heteromyias albispecularis | gyhrob1 |
| Grey-headed Robin | Heteromyias cinereifrons | Gray-headed Robin | Heteromyias cinereifrons | gyhrob2 |
| Grey Sibia | Heterophasia gracilis | Gray Sibia | Heterophasia gracilis | grysib1 |
| Rüppell's Korhaan | Heterotetrax rueppelii | Rüppell's Bustard | Heterotetrax rueppelii | ruebus1 |
| Blue Swallow | Hirundo atrocaerulea | Montane Blue Swallow | Hirundo atrocaerulea | bluswa1 |
| Dohrn's Warbler | Sylvia dohrni | Dohrn's Thrush-Babbler | Sylvia dohrni | dohthb1 |
| Brown-flanked Bush Warbler | Horornis fortipes | Brownish-flanked Bush Warbler | Horornis fortipes | bfbwar1 |
| Gilded Sapphire | Hylocharis chrysura | Gilded Hummingbird | Hylocharis chrysura | gilhum1 |
| Grey-eyed Greenlet | Hylophilus amaurocephalus | Gray-eyed Greenlet | Hylophilus amaurocephalus | gyegre1 |
| Ochre-crowned Greenlet | Tunchiornis ochraceiceps | Ochre-crowned Brownlet | Tunchiornis ochraceiceps | tacgre2 |
| Grey-chested Greenlet | Hylophilus semicinereus | Gray-chested Greenlet | Hylophilus semicinereus | gycgre1 |
| Grey Hypocolius | Hypocolius ampelinus | Hypocolius | Hypocolius ampelinus | hypoco1 |
| Grey-headed Fish Eagle | Icthyophaga ichthyaetus | Gray-headed Fish-Eagle | Icthyophaga ichthyaetus | gyhfie1 |
| Blue-capped Ifrit | Ifrita kowaldi | Blue-capped Ifrita | Ifrita kowaldi | bucifr1 |
| Grey-winged Inca Finch | Incaspiza ortizi | Gray-winged Inca-Finch | Incaspiza ortizi | gywinf1 |
| Malaysian Honeyguide | Indicator archipelagicus | Malayan Honeyguide | Indicator archipelagicus | malhon1 |
| Pale-tipped Inezia | Inezia caudata | Pale-tipped Tyrannulet | Inezia caudata | pattyr3 |
| Plain Inezia | Inezia inornata | Plain Tyrannulet | Inezia inornata | platyr1 |
| Amazonian Inezia | Inezia subflava | Amazonian Tyrannulet | Inezia subflava | amatyr1 |
| Slender-billed Inezia | Inezia tenuirostris | Slender-billed Tyrannulet | Inezia tenuirostris | slbtyr1 |
| Grey-eyed Bulbul | Iole propinqua | Gray-eyed Bulbul | Iole propinqua | gyebul1 |
| Von Schrenck's Bittern | Botaurus eurhythmus | Schrenck's Bittern | Botaurus eurhythmus | schbit1 |
| Grey-chested Babbler | Kakamega poliothorax | Gray-chested Babbler | Kakamega poliothorax | gycill1 |
| Grey-capped Hemispingus | Kleinothraupis reyi | Gray-capped Hemispingus | Kleinothraupis reyi | gychem1 |
| Plumbeous Tyrant | Knipolegus cabanisi | Plumbeous Black-Tyrant | Knipolegus cabanisi | andtyr2 |
| Red-collared Babbler | Turdoides rufocinctus | Red-collared Mountain-Babbler | Turdoides rufocinctus | rcmbab1 |
| Pied Starling | Lamprotornis bicolor | African Pied Starling | Lamprotornis bicolor | afpsta1 |
| Crimson-breasted Shrike | Laniarius atrococcineus | Crimson-breasted Gonolek | Laniarius atrococcineus | crbgon1 |
| Mountain Sooty Boubou | Laniarius poensis | Western Boubou | Laniarius poensis | mosbou1 |
| East Coast Boubou | Laniarius sublacteus | Zanzibar Boubou | Laniarius sublacteus | zanbou1 |
| Great Grey Shrike | Lanius excubitor | Great Gray Shrike | Lanius excubitor | norshr1 |
| Grey-backed Fiscal | Lanius excubitoroides | Gray-backed Fiscal | Lanius excubitoroides | gybfis1 |
| Iberian Grey Shrike | Lanius meridionalis | Iberian Gray Shrike | Lanius meridionalis | ibgshr1 |
| Lesser Grey Shrike | Lanius minor | Lesser Gray Shrike | Lanius minor | legshr2 |
| Chinese Grey Shrike | Lanius sphenocercus | Chinese Gray Shrike | Lanius sphenocercus | chgshr1 |
| Grey-backed Shrike | Lanius tephronotus | Gray-backed Shrike | Lanius tephronotus | gybshr1 |
| Grey-breasted Crake | Laterallus exilis | Gray-breasted Crake | Laterallus exilis | grbcra1 |
| Galapagos Crake | Laterallus spilonota | Galapagos Rail | Laterallus spilonota | galrai1 |
| Grey-breasted Flycatcher | Lathrotriccus griseipectus | Gray-breasted Flycatcher | Lathrotriccus griseipectus | gybfly1 |
| Madagascar Mannikin | Lepidopygia nana | Madagascar Munia | Lepidopygia nana | madmun1 |
| Bagobo Babbler | Leonardina woodi | Bagobo Robin | Leonardina woodi | bagbab2 |
| Streak-backed Tit-Spinetail | Leptasthenura striata | Streaked Tit-Spinetail | Leptasthenura striata | sttspi1 |
| Grey-headed Kite | Leptodon cayanensis | Gray-headed Kite | Leptodon cayanensis | grhkit1 |
| Grey-chested Dove | Leptotila cassinii | Gray-chested Dove | Leptotila cassinii | grcdov1 |
| Yungas Dove | Leptotila megalura | Large-tailed Dove | Leptotila megalura | latdov1 |
| Grey-headed Dove | Leptotila plumbeiceps | Gray-headed Dove | Leptotila plumbeiceps | gyhdov1 |
| Grey-fronted Dove | Leptotila rufaxilla | Gray-fronted Dove | Leptotila rufaxilla | grfdov1 |
| Imperial Shag | Leucocarbo atriceps | Imperial Cormorant | Leucocarbo atriceps | impcor6 |
| Rock Shag | Leucocarbo magellanicus | Magellanic Cormorant | Leucocarbo magellanicus | magcor1 |
| Grey Gull | Leucophaeus modestus | Gray Gull | Leucophaeus modestus | grygul |
| Bali Starling | Leucopsar rothschildi | Bali Myna | Leucopsar rothschildi | balmyn1 |
| Grey-backed Hawk | Pseudastur occidentalis | Gray-backed Hawk | Pseudastur occidentalis | gybhaw2 |
| Brandt's Mountain Finch | Leucosticte brandti | Black-headed Mountain Finch | Leucosticte brandti | bhmfin1 |
| Grey-crowned Rosy Finch | Leucosticte tephrocotis | Gray-crowned Rosy-Finch | Leucosticte tephrocotis | gcrfin |
| Flame-eared Honeyeater | Lichmera flavicans | Yellow-eared Honeyeater | Lichmera flavicans | yeehon1 |
| Grey-eared Honeyeater | Lichmera incana | Gray-eared Honeyeater | Lichmera incana | dabhon1 |
| Scaly-breasted Honeyeater | Lichmera squamata | White-tufted Honeyeater | Lichmera squamata | whthon2 |
| Grey-winged Cotinga | Lipaugus conditus | Gray-winged Cotinga | Lipaugus conditus | gywcot1 |
| Chestnut-breasted Mannikin | Lonchura castaneothorax | Chestnut-breasted Munia | Lonchura castaneothorax | chbmun1 |
| Hooded Mannikin | Lonchura spectabilis | Hooded Munia | Lonchura spectabilis | hoomun1 |
| Grey-banded Mannikin | Lonchura vana | Gray-banded Munia | Lonchura vana | gybmun1 |
| African Grey Hornbill | Lophoceros nasutus | African Gray Hornbill | Lophoceros nasutus | afghor1 |
| Grey-crested Tit | Lophophanes dichrous | Gray-crested Tit | Lophophanes dichrous | gyctit1 |
| Grey-crested Finch | Lophospingus griseocristatus | Gray-crested Finch | Lophospingus griseocristatus | gycfin1 |
| Great Hanging Parrot | Loriculus stigmatus | Sulawesi Hanging-Parrot | Loriculus stigmatus | suhpar1 |
| Two-barred Crossbill | Loxia leucoptera | White-winged Crossbill | Loxia leucoptera | whwcro |
| Malaysian Eared Nightjar | Lyncornis temminckii | Malayan Eared-Nightjar | Lyncornis temminckii | malnig1 |
| Indian Black-lored Tit | Machlolophus aplonotus | Indian Yellow Tit | Machlolophus aplonotus | indtit1 |
| Yellow Tit | Machlolophus holsti | Taiwan Yellow Tit | Machlolophus holsti | yeltit2 |
| Golden-tufted Mountain Grackle | Macroagelaius imthurni | Golden-tufted Grackle | Macroagelaius imthurni | gotgra1 |
| Colombian Mountain Grackle | Macroagelaius subalaris | Mountain Grackle | Macroagelaius subalaris | mougra1 |
| Grey-cheeked Tit-Babbler | Mixornis flavicollis | Gray-cheeked Tit-Babbler | Mixornis flavicollis | gyctib1 |
| Grey-faced Tit-Babbler | Mixornis kelleyi | Gray-faced Tit-Babbler | Mixornis kelleyi | gyftib1 |
| Cape Longclaw | Macronyx capensis | Orange-throated Longclaw | Macronyx capensis | ortlon1 |
| Bar-tailed Cuckoo-Dove | Macropygia nigrirostris | Black-billed Cuckoo-Dove | Macropygia nigrirostris | bbcdov1 |
| Grey Longbill | Macrosphenus concolor | Gray Longbill | Macrosphenus concolor | grylon1 |
| Grey-headed Bushshrike | Malaconotus blanchoti | Gray-headed Bushshrike | Malaconotus blanchoti | gyhbus1 |
| Grey-breasted Babbler | Malacopteron albogulare | Gray-breasted Babbler | Malacopteron albogulare | gybbab1 |
| Cassin's Malimbe | Malimbus cassini | Black-throated Malimbe | Malimbus cassini | bltmal1 |
| Star-chested Treerunner | Margarornis stellatus | Fulvous-dotted Treerunner | Margarornis stellatus | fudtre1 |
| New Guinea Scrubfowl | Megapodius decollatus | New Guinea Megapode | Megapodius decollatus | negscr1 |
| Biak Scrubfowl | Megapodius geelvinkianus | Biak Megapode | Megapodius geelvinkianus | dusscr3 |
| Orange-footed Scrubfowl | Megapodius reinwardt | Orange-footed Megapode | Megapodius reinwardt | orfscr1 |
| Yungas Screech Owl | Megascops hoyi | Montane Forest Screech-Owl | Megascops hoyi | mofsco1 |
| West Peruvian Screech Owl | Megascops roboratus | Peruvian Screech-Owl | Megascops roboratus | persco1 |
| Grey-breasted Woodpecker | Melanerpes hypopolius | Gray-breasted Woodpecker | Melanerpes hypopolius | grbwoo1 |
| Grey Tit | Melaniparus afer | Gray Tit | Melaniparus afer | grytit1 |
| Acacia Tit | Melaniparus thruppi | Somali Tit | Melaniparus thruppi | somtit4 |
| Slaty Robin | Melanodryas cyanus | Blue-gray Robin | Melanodryas cyanus | bugrob1 |
| Maranon Crescentchest | Melanopareia maranonica | Marañon Crescentchest | Melanopareia maranonica | marcre1 |
| Common Smoky Honeyeater | Melipotes fumigatus | Smoky Honeyeater | Melipotes fumigatus | smohon1 |
| Prevost's Ground Sparrow | Melozone biarcuata | White-faced Ground-Sparrow | Melozone biarcuata | pregrs1 |
| Ruspoli's Turaco | Menelikornis ruspolii | Prince Ruspoli's Turaco | Menelikornis ruspolii | prrtur1 |
| Fiery-throated Metaltail | Metallura eupogon | Fire-throated Metaltail | Metallura eupogon | fitmet1 |
| Moreno's Ground Dove | Metriopelia morenoi | Bare-eyed Ground Dove | Metriopelia morenoi | begdov1 |
| Southern Nightingale-Wren | Microcerculus marginatus | Scaly-breasted Wren | Microcerculus marginatus | scbwre1 |
| Northern Nightingale-Wren | Microcerculus philomela | Nightingale Wren | Microcerculus philomela | nigwre1 |
| Grey-throated Warbling Finch | Microspingus cabanisi | Gray-throated Warbling Finch | Microspingus cabanisi | gytwaf1 |
| Grey-headed Bulbul | Microtarsus priocephalus | Gray-headed Bulbul | Microtarsus priocephalus | gyhbul1 |
| Espanola Mockingbird | Mimus macdonaldi | Española Mockingbird | Mimus macdonaldi | hoomoc1 |
| Olive-striped Flycatcher | Mionectes olivaceus | Olive-streaked Flycatcher | Mionectes olivaceus | olsfly2 |
| Grey-hooded Flycatcher | Mionectes rufiventris | Gray-hooded Flycatcher | Mionectes rufiventris | gyhfly1 |
| Northern Tufted Flycatcher | Mitrephanes phaeocercus | Tawny Tufted-Flycatcher | Mitrephanes phaeocercus | tuffly1 |
| Russet-crowned Motmot | Momotus mexicanus | Mexican Motmot | Momotus mexicanus | rucmot1 |
| Common Rock Thrush | Monticola saxatilis | Rufous-tailed Rock-Thrush | Monticola saxatilis | rtrthr1 |
| Grey Wagtail | Motacilla cinerea | Gray Wagtail | Motacilla cinerea | grywag |
| Grey-streaked Flycatcher | Muscicapa griseisticta | Gray-streaked Flycatcher | Muscicapa griseisticta | gysfly1 |
| Shear-tailed Grey Tyrant | Muscipipra vetula | Shear-tailed Gray Tyrant | Muscipipra vetula | shtgrt1 |
| Paramo Ground Tyrant | Muscisaxicola alpinus | Plain-capped Ground-Tyrant | Muscisaxicola alpinus | plcgrt1 |
| Biak Black Flycatcher | Myiagra atra | Biak Flycatcher | Myiagra atra | biafly1 |
| Black-tailed Myiobius | Myiobius atricaudus | Black-tailed Flycatcher | Myiobius atricaudus | bltfly1 |
| Whiskered Myiobius | Myiobius barbatus | Whiskered Flycatcher | Myiobius barbatus | whifly1 |
| Sulphur-rumped Myiobius | Myiobius sulphureipygius | Sulphur-rumped Flycatcher | Myiobius sulphureipygius | surfly1 |
| Tawny-breasted Myiobius | Myiobius villosus | Tawny-breasted Flycatcher | Myiobius villosus | tabfly1 |
| White-bellied Blue Robin | Sholicola albiventris | White-bellied Sholakili | Sholicola albiventris | whbsho3 |
| Nilgiri Blue Robin | Sholicola major | Nilgiri Sholakili | Sholicola major | whbsho1 |
| Grey-headed Elaenia | Myiopagis caniceps | Gray-headed Elaenia | Myiopagis caniceps | gryela3 |
| Mouse-grey Flycatcher | Myiophobus crypterythrus | Mouse-gray Flycatcher | Myiophobus crypterythrus | brcfly4 |
| Grey-throated Warbler | Myiothlypis cinereicollis | Gray-throated Warbler | Myiothlypis cinereicollis | gytwar1 |
| Grey-and-gold Warbler | Myiothlypis fraseri | Gray-and-gold Warbler | Myiothlypis fraseri | gagwar2 |
| Grey-headed Warbler | Myiothlypis griseiceps | Gray-headed Warbler | Myiothlypis griseiceps | gyhwar1 |
| White-rimmed Warbler | Myiothlypis leucoblephara | White-browed Warbler | Myiothlypis leucoblephara | whbwar2 |
| Grey-capped Flycatcher | Myiozetetes granadensis | Gray-capped Flycatcher | Myiozetetes granadensis | grcfly1 |
| Blue Whistling Thrush | Myophonus caeruleus | Chinese Whistling-Thrush | Myophonus caeruleus | bluwht1 |
| Brown-winged Whistling Thrush | Myophonus castaneus | Sumatran Whistling-Thrush | Myophonus castaneus | chwwht1 |
| Malayan Whistling Thrush | Myophonus robinsoni | Malaysian Whistling-Thrush | Myophonus robinsoni | mawthr2 |
| Southern Chestnut-tailed Antbird | Sciaphylax hemimelaena | Chestnut-tailed Antbird | Sciaphylax hemimelaena | chtant2 |
| Anteater Chat | Myrmecocichla aethiops | Northern Anteater-Chat | Myrmecocichla aethiops | noacha1 |
| Ant-eating Chat | Myrmecocichla formicivora | Southern Anteater-Chat | Myrmecocichla formicivora | soacha1 |
| Rüppell's Black Chat | Myrmecocichla melaena | Rüppell's Chat | Myrmecocichla melaena | ruecha1 |
| Yungas Antwren | Myrmotherula grisea | Ashy Antwren | Myrmotherula grisea | ashant1 |
| Grey Antwren | Myrmotherula menetriesii | Gray Antwren | Myrmotherula menetriesii | gryant1 |
| Mountain Myzomela | Myzomela adolphinae | Elfin Myzomela | Myzomela adolphinae | moumyz1 |
| Banda Myzomela | Myzomela boiei | Banda Islands Myzomela | Myzomela boiei | banmyz2 |
| Manu Parrotlet | Nannopsittaca dachilleae | Amazonian Parrotlet | Nannopsittaca dachilleae | amapar1 |
| Scarlet-tufted Sunbird | Nectarinia johnstoni | Red-tufted Sunbird | Nectarinia johnstoni | retsun2 |
| Grey Monjita | Nengetus cinereus | Gray Monjita | Nengetus cinereus | grymon1 |
| Finsch's Rufous Thrush | Stizorhina finschi | Finsch's Flycatcher-Thrush | Stizorhina finschi | fifthr1 |
| Fraser's Rufous Thrush | Stizorhina fraseri | Rufous Flycatcher-Thrush | Stizorhina fraseri | rufthr1 |
| Cinnamon Neopipo | Neopipo cinnamomea | Cinnamon Manakin-Tyrant | Neopipo cinnamomea | cinmat1 |
| Shrike-like Tanager | Neothraupis fasciata | White-banded Tanager | Neothraupis fasciata | whbtan1 |
| Maranon Tyrannulet | Nesotriccus maranonicus | Marañon Tyrannulet | Nesotriccus maranonicus | moctyr4 |
| Grey-headed Nigrita | Nigrita canicapillus | Gray-headed Nigrita | Nigrita canicapillus | gyhneg1 |
| Christmas Boobook | Ninox natalis | Christmas Island Boobook | Ninox natalis | chihao1 |
| Grey-cheeked Nunlet | Nonnula frontalis | Gray-cheeked Nunlet | Nonnula frontalis | gycnun1 |
| Eastern Bluebonnet | Northiella haematogaster | Greater Bluebonnet | Northiella haematogaster | bluebo1 |
| Pauraque | Nyctidromus albicollis | Common Pauraque | Nyctidromus albicollis | compau |
| Anthony's Nightjar | Nyctidromus anthonyi | Scrub Nightjar | Nyctidromus anthonyi | scrnig1 |
| Plain-tailed Nighthawk | Nyctiprogne vielliardi | Bahian Nighthawk | Nyctiprogne vielliardi | bahnig1 |
| Slaty-backed Chat-Tyrant | Ochthoeca cinnamomeiventris | Chestnut-bellied Chat-Tyrant | Ochthoeca cinnamomeiventris | slbcht2 |
| Tumbes Tyrant | Ochthoeca salvini | Tumbes Chat-Tyrant | Ochthoeca salvini | tumtyr2 |
| Indian Grey Hornbill | Ocyceros birostris | Indian Gray Hornbill | Ocyceros birostris | inghor2 |
| Sri Lanka Grey Hornbill | Ocyceros gingalensis | Sri Lanka Gray Hornbill | Ocyceros gingalensis | ceghor1 |
| Malabar Grey Hornbill | Ocyceros griseus | Malabar Gray Hornbill | Ocyceros griseus | maghor2 |
| Grey-mantled Wren | Odontorchilus branickii | Gray-mantled Wren | Odontorchilus branickii | gymwre1 |
| Grey-headed Silverbill | Spermestes griseicapilla | Gray-headed Silverbill | Spermestes griseicapilla | gyhsil1 |
| Red-tailed Wheatear | Oenanthe chrysopygia | Persian Wheatear | Oenanthe chrysopygia | retwhe2 |
| Brown-tailed Rock Chat | Oenanthe scotocerca | Brown-tailed Chat | Oenanthe scotocerca | brtcha1 |
| Spectacled Tern | Onychoprion lunatus | Gray-backed Tern | Onychoprion lunatus | gybter1 |
| Western Oriole | Oriolus brachyrynchus | Western Black-headed Oriole | Oriolus brachyrynchus | wbhori1 |
| Grey-collared Oriole | Oriolus forsteni | Seram Oriole | Oriolus forsteni | serori1 |
| Black-headed Oriole | Oriolus larvatus | African Black-headed Oriole | Oriolus larvatus | abhori1 |
| Ethiopian Oriole | Oriolus monacha | Ethiopian Black-headed Oriole | Oriolus monacha | dahori1 |
| Dusky-brown Oriole | Oriolus phaeochromus | Halmahera Oriole | Oriolus phaeochromus | halori1 |
| Grey-headed Chachalaca | Ortalis cinereiceps | Gray-headed Chachalaca | Ortalis cinereiceps | grhcha1 |
| Little Chachalaca | Ortalis motmot | Variable Chachalaca | Ortalis motmot | varcha1 |
| Grey-backed Tailorbird | Orthotomus derbianus | Gray-backed Tailorbird | Orthotomus derbianus | gybtai1 |
| Black-headed Tailorbird | Orthotomus nigriceps | White-browed Tailorbird | Orthotomus nigriceps | whbtai1 |
| Grey Francolin | Ortygornis pondicerianus | Gray Francolin | Ortygornis pondicerianus | gryfra |
| Karthala Scops Owl | Otus pauliani | Comoro Scops-Owl | Otus pauliani | cosowl3 |
| Melanesian Whistler | Pachycephala chlorura | Vanuatu Whistler | Pachycephala chlorura | necwhi2 |
| Rusty-breasted Whistler | Pachycephala calliope | Tenggara Whistler | Pachycephala calliope | rubwhi1 |
| Yellow-throated Whistler | Pachycephala macrorhyncha | Moluccan Whistler | Pachycephala macrorhyncha | yetwhi1 |
| Grey Whistler | Pachycephala simplex | Gray Whistler | Pachycephala simplex | grywhi2 |
| Sulphur-vented Whistler | Pachycephala sulfuriventer | Sulphur-bellied Whistler | Pachycephala sulfuriventer | subwhi1 |
| Legge's Flowerpecker | Pachyglossa vincens | White-throated Flowerpecker | Pachyglossa vincens | whtflo1 |
| Grey-collared Becard | Pachyramphus major | Gray-collared Becard | Pachyramphus major | grcbec1 |
| Grey-headed Parrotbill | Paradoxornis gularis | Gray-headed Parrotbill | Paradoxornis gularis | gyhpar3 |
| Queen Carola's Parotia | Parotia carolae | Carola's Parotia | Parotia carolae | carpar1 |
| Southern Grey-headed Sparrow | Passer diffusus | Southern Gray-headed Sparrow | Passer diffusus | sghspa2 |
| Northern Grey-headed Sparrow | Passer griseus | Northern Gray-headed Sparrow | Passer griseus | gyhspa1 |
| Iago Sparrow | Passer iagoensis | Cape Verde Sparrow | Passer iagoensis | cavspa1 |
| Great Sparrow | Passer motitensis | Great Rufous Sparrow | Passer motitensis | grrspa1 |
| Kenya Sparrow | Passer rufocinctus | Kenya Rufous Sparrow | Passer rufocinctus | kerspa2 |
| Shelley's Sparrow | Passer shelleyi | Shelley's Rufous Sparrow | Passer shelleyi | shrspa1 |
| Maranon Pigeon | Patagioenas oenops | Peruvian Pigeon | Patagioenas oenops | perpig2 |
| Giant Hummingbird | Patagona gigas | Southern Giant-Hummingbird | Patagona gigas | giahum3 |
| Grey Partridge | Perdix perdix | Gray Partridge | Perdix perdix | grypar |
| Swinhoe's Minivet | Pericrocotus cantonensis | Brown-rumped Minivet | Pericrocotus cantonensis | brrmin1 |
| Little Minivet | Pericrocotus lansbergei | Flores Minivet | Pericrocotus lansbergei | flomin1 |
| Grey-chinned Minivet | Pericrocotus solaris | Gray-chinned Minivet | Pericrocotus solaris | gycmin1 |
| Crested Honey Buzzard | Pernis ptilorhynchus | Oriental Honey-buzzard | Pernis ptilorhynchus | orihob2 |
| Preuss's Cliff Swallow | Petrochelidon preussi | Preuss's Swallow | Petrochelidon preussi | preswa2 |
| American Cliff Swallow | Petrochelidon pyrrhonota | Cliff Swallow | Petrochelidon pyrrhonota | cliswa |
| Red-throated Cliff Swallow | Petrochelidon rufigula | Red-throated Swallow | Petrochelidon rufigula | retswa2 |
| South African Cliff Swallow | Petrochelidon spilodera | South African Swallow | Petrochelidon spilodera | soaswa2 |
| Mountain Robin | Petroica bivittata | Subalpine Robin | Petroica bivittata | alprob1 |
| Grey-chinned Hermit | Phaethornis griseogularis | Gray-chinned Hermit | Phaethornis griseogularis | gycher1 |
| Black-and-yellow Phainoptila | Phainoptila melanoxantha | Black-and-yellow Silky-flycatcher | Phainoptila melanoxantha | bayfly1 |
| Australian Pied Cormorant | Phalacrocorax varius | Pied Cormorant | Phalacrocorax varius | piecor1 |
| Common Pheasant | Phasianus colchicus | Ring-necked Pheasant | Phasianus colchicus | rinphe1 |
| Grey-browed Wren | Pheugopedius schulenbergi | Gray-browed Wren | Pheugopedius schulenbergi | pltwre3 |
| Manus Friarbird | Philemon albitorques | White-naped Friarbird | Philemon albitorques | whnfri1 |
| Forest Wood Hoopoe | Rhinopomastus castaneiceps | Forest Scimitarbill | Rhinopomastus castaneiceps | forwoo1 |
| Przevalski's Redstart | Phoenicurus alaschanicus | Ala Shan Redstart | Phoenicurus alaschanicus | alsred1 |
| Güldenstädt's Redstart | Phoenicurus erythrogastrus | White-winged Redstart | Phoenicurus erythrogastrus | whwred2 |
| Eversmann's Redstart | Phoenicurus erythronotus | Rufous-backed Redstart | Phoenicurus erythronotus | rubred2 |
| Plumbeous Water Redstart | Phoenicurus fuliginosus | Plumbeous Redstart | Phoenicurus fuliginosus | plured1 |
| Grey-hooded Sierra Finch | Phrygilus gayi | Gray-hooded Sierra Finch | Phrygilus gayi | gyhsif1 |
| Baumann's Olive Greenbul | Phyllastrephus baumanni | Baumann's Greenbul | Phyllastrephus baumanni | baugre1 |
| Grey-olive Greenbul | Phyllastrephus cerviniventris | Gray-olive Greenbul | Phyllastrephus cerviniventris | gyogre1 |
| Lowland Tiny Greenbul | Phyllastrephus debilis | Tiny Greenbul | Phyllastrephus debilis | tingre1 |
| Grey-headed Greenbul | Phyllastrephus poliocephalus | Gray-headed Greenbul | Phyllastrephus poliocephalus | gyhgre1 |
| Grey-capped Tyrannulet | Phyllomyias griseocapilla | Gray-capped Tyrannulet | Phyllomyias griseocapilla | gyctyr1 |
| Panama Tyrannulet | Phylloscartes flavovirens | Yellow-green Tyrannulet | Phylloscartes flavovirens | yegtyr1 |
| Grey-cheeked Warbler | Phylloscopus poliogenys | Gray-cheeked Warbler | Phylloscopus poliogenys | gycwar2 |
| Grey-crowned Warbler | Phylloscopus tephrocephalus | Gray-crowned Warbler | Phylloscopus tephrocephalus | gycwar1 |
| Grey-hooded Warbler | Phylloscopus xanthoschistos | Gray-hooded Warbler | Phylloscopus xanthoschistos | gyhwar2 |
| Yellow-browed Woodpecker | Piculus aurulentus | White-browed Woodpecker | Piculus aurulentus | whbwoo7 |
| Greyish Piculet | Picumnus granadensis | Grayish Piculet | Picumnus granadensis | grapic1 |
| Japanese Green Woodpecker | Picus awokera | Japanese Woodpecker | Picus awokera | japwoo1 |
| Grey-headed Woodpecker | Picus canus | Gray-headed Woodpecker | Picus canus | gyfwoo1 |
| European Green Woodpecker | Picus viridis | Eurasian Green Woodpecker | Picus viridis | eugwoo2 |
| Grey-headed Piprites | Piprites griseiceps | Gray-headed Piprites | Piprites griseiceps | grhpip1 |
| Taveta Weaver | Ploceus castaneiceps | Taveta Golden-Weaver | Ploceus castaneiceps | tagwea1 |
| Eastern Golden Weaver | Ploceus subaureus | African Golden-Weaver | Ploceus subaureus | afgwea1 |
| Grey Plover | Pluvialis squatarola | Black-bellied Plover | Pluvialis squatarola | bkbplo |
| Black-necked Grebe | Podiceps nigricollis | Eared Grebe | Podiceps nigricollis | eargre |
| Grey-headed Chickadee | Poecile cinctus | Gray-headed Chickadee | Poecile cinctus | gyhchi |
| Grey-and-gold Tanager | Poecilostreptus palmeri | Gray-and-gold Tanager | Poecilostreptus palmeri | gagtan1 |
| Lulu's Tody-Flycatcher | Poecilotriccus luluae | Johnson's Tody-Flycatcher | Poecilotriccus luluae | johtot1 |
| Slaty-headed Tody-Flycatcher | Poecilotriccus sylvia | Slate-headed Tody-Flycatcher | Poecilotriccus sylvia | shtfly1 |
| Maranon Gnatcatcher | Polioptila maior | Marañon Gnatcatcher | Polioptila maior | trogna3 |
| Blue-grey Gnatcatcher | Polioptila caerulea | Blue-gray Gnatcatcher | Polioptila caerulea | buggna |
| Grey Peacock-Pheasant | Polyplectron bicalcaratum | Gray Peacock-Pheasant | Polyplectron bicalcaratum | grypep2 |
| Grey-backed Tachuri | Polystictus superciliaris | Gray-backed Tachuri | Polystictus superciliaris | gybtac1 |
| Grey-crowned Babbler | Pomatostomus temporalis | Gray-crowned Babbler | Pomatostomus temporalis | gycbab1 |
| Purple Swamphen | Porphyrio porphyrio | Western Swamphen | Porphyrio porphyrio | purswa1 |
| Golden-collared Macaw | Primolius auricollis | Yellow-collared Macaw | Primolius auricollis | yecmac |
| Grey-crowned Prinia | Prinia cinereocapilla | Gray-crowned Prinia | Prinia cinereocapilla | gycpri1 |
| Grey-breasted Prinia | Prinia hodgsonii | Gray-breasted Prinia | Prinia hodgsonii | gybpri1 |
| Blue-crowned Racket-tail | Prioniturus discurus | Blue-crowned Racquet-tail | Prioniturus discurus | bcrtai1 |
| Green Racket-tail | Prioniturus luconensis | Green Racquet-tail | Prioniturus luconensis | grrtai1 |
| Blue-headed Racket-tail | Prioniturus platenae | Blue-headed Racquet-tail | Prioniturus platenae | bhrtai1 |
| Golden-mantled Racket-tail | Prioniturus platurus | Golden-mantled Racquet-tail | Prioniturus platurus | gmrtai1 |
| Grey Petrel | Procellaria cinerea | Gray Petrel | Procellaria cinerea | grapet |
| Black Petrel | Procellaria parkinsoni | Parkinson's Petrel | Procellaria parkinsoni | parpet1 |
| Grey-breasted Martin | Progne chalybea | Gray-breasted Martin | Progne chalybea | gybmar |
| Kozlov's Accentor | Prunella koslowi | Mongolian Accentor | Prunella koslowi | monacc1 |
| American Bushtit | Psaltriparus minimus | Bushtit | Psaltriparus minimus | bushti |
| Grey-and-white Tyrannulet | Pseudelaenia leucospodia | Gray-and-white Tyrannulet | Pseudelaenia leucospodia | gawtyr2 |
| Grey-rumped Swallow | Pseudhirundo griseopyga | Gray-rumped Swallow | Pseudhirundo griseopyga | gyrswa1 |
| Grey-capped Social Weaver | Pseudonigrita arnaudi | Gray-capped Social-Weaver | Pseudonigrita arnaudi | gyhsow1 |
| Grey-crested Cacholote | Pseudoseisura unirufa | Rufous Cacholote | Pseudoseisura unirufa | rufcac2 |
| Golden-whiskered Barbet | Psilopogon chrysopogon | Gold-whiskered Barbet | Psilopogon chrysopogon | gowbar2 |
| Grey-hooded Parakeet | Psilopsiagon aymara | Gray-hooded Parakeet | Psilopsiagon aymara | gyhpar1 |
| Blue-winged Parakeet | Psittacula columboides | Malabar Parakeet | Psittacula columboides | malpar1 |
| Lord Derby's Parakeet | Psittacula derbiana | Derbyan Parakeet | Psittacula derbiana | derpar1 |
| Grey-headed Parakeet | Psittacula finschii | Gray-headed Parakeet | Psittacula finschii | gyhpar2 |
| Grey Parrot | Psittacus erithacus | Gray Parrot | Psittacus erithacus | grepar |
| Grey-winged Trumpeter | Psophia crepitans | Gray-winged Trumpeter | Psophia crepitans | gywtru1 |
| Grey-faced Petrel | Pterodroma gouldi | Gray-faced Petrel | Pterodroma gouldi | grwpet2 |
| Banded Fruit Dove | Ptilinopus cinctus | Black-backed Fruit-Dove | Ptilinopus cinctus | bbfdov1 |
| Grey Silky-flycatcher | Ptiliogonys cinereus | Gray Silky-flycatcher | Ptiliogonys cinereus | grsfly1 |
| Grey-streaked Honeyeater | Ptiloprora perstriata | Gray-streaked Honeyeater | Ptiloprora perstriata | blbhon1 |
| Blue Jewel-babbler | Ptilorrhoa caerulescens | Northern Blue Jewel-babbler | Ptilorrhoa caerulescens | blujeb1 |
| Grey-headed Honeyeater | Ptilotula keartlandi | Gray-headed Honeyeater | Ptilotula keartlandi | gyhhon1 |
| Grey-fronted Honeyeater | Ptilotula plumula | Gray-fronted Honeyeater | Ptilotula plumula | gyfhon1 |
| Large Rock Martin | Ptyonoprogne fuligula | Southern Crag-Martin | Ptyonoprogne fuligula | rocmar5 |
| Mediterranean Shearwater | Puffinus yelkouan | Yelkouan Shearwater | Puffinus yelkouan | levshe1 |
| Asian Red-eyed Bulbul | Pycnonotus brunneus | Red-eyed Bulbul | Pycnonotus brunneus | reebul1 |
| African Red-eyed Bulbul | Pycnonotus nigricans | Black-fronted Bulbul | Pycnonotus nigricans | blfbul1 |
| Alpine Chough | Pyrrhocorax graculus | Yellow-billed Chough | Pyrrhocorax graculus | yebcho1 |
| Golden-naped Finch | Pyrrhoplectes epauletta | Gold-naped Finch | Pyrrhoplectes epauletta | gonfin1 |
| Grey-headed Bullfinch | Pyrrhula erythaca | Gray-headed Bullfinch | Pyrrhula erythaca | gyhbul2 |
| White-breasted Parakeet | Pyrrhura albipectus | White-necked Parakeet | Pyrrhura albipectus | whnpar1 |
| Flame-winged Parakeet | Pyrrhura calliptera | Brown-breasted Parakeet | Pyrrhura calliptera | brbpar2 |
| White-eared Parakeet | Pyrrhura leucotis | Maroon-faced Parakeet | Pyrrhura leucotis | mafpar3 |
| Grey-breasted Parakeet | Pyrrhura griseipectus | Gray-breasted Parakeet | Pyrrhura griseipectus | gybpar1 |
| Blood-eared Parakeet | Pyrrhura hoematotis | Red-eared Parakeet | Pyrrhura hoematotis | reepar1 |
| Rose-crowned Parakeet | Pyrrhura rhodocephala | Rose-headed Parakeet | Pyrrhura rhodocephala | rohpar1 |
| Trilling Gnatwren | Ramphocaenus melanurus | Long-billed Gnatwren | Ramphocaenus melanurus | lobgna5 |
| Huallaga Tanager | Ramphocelus melanogaster | Black-bellied Tanager | Ramphocelus melanogaster | bkbtan1 |
| White-throated Jungle Flycatcher | Vauriella albigularis | Negros Jungle Flycatcher | Vauriella albigularis | negjuf1 |
| Grey Fantail | Rhipidura albiscapa | Gray Fantail | Rhipidura albiscapa | gryfan1 |
| White-spotted Fantail | Rhipidura albogularis | Spot-breasted Fantail | Rhipidura albogularis | spbfan1 |
| Cinnamon-tailed Fantail | Rhipidura fuscorufa | Tremolo Fantail | Rhipidura fuscorufa | citfan1 |
| Arabian Golden-winged Grosbeak | Rhynchostruthus percivali | Arabian Grosbeak | Rhynchostruthus percivali | gowgro2 |
| Greyish Mourner | Rhytipterna simplex | Grayish Mourner | Rhytipterna simplex | gramou1 |
| Grey-throated Martin | Riparia chinensis | Gray-throated Martin | Riparia chinensis | gytmar1 |
| Brown-throated Martin | Riparia paludicola | Plain Martin | Riparia paludicola | plamar1 |
| Sand Martin | Riparia riparia | Bank Swallow | Riparia riparia | banswa |
| Grey-bellied Bulbul | Rubigula cyaniventris | Gray-bellied Bulbul | Rubigula cyaniventris | gybbul1 |
| Bluish-grey Saltator | Saltator coerulescens | Bluish-gray Saltator | Saltator coerulescens | grasal3 |
| Olive-grey Saltator | Saltator olivascens | Olive-gray Saltator | Saltator olivascens | grasal4 |
| Orinoco Saltator | Saltator orenocensis | Orinocan Saltator | Saltator orenocensis | orisal1 |
| Canary Islands Stonechat | Saxicola dacotiae | Fuerteventura Stonechat | Saxicola dacotiae | caisto1 |
| Grey Bush Chat | Saxicola ferreus | Gray Bushchat | Saxicola ferreus | grybus1 |
| White-bellied Bush Chat | Saxicola gutturalis | Timor Bushchat | Saxicola gutturalis | timbus1 |
| Winifred's Warbler | Scepomycter winifredae | Mrs. Moreau's Warbler | Scepomycter winifredae | mrmwar1 |
| Guianan Schiffornis | Schiffornis olivacea | Olivaceous Schiffornis | Schiffornis olivacea | thlsch7 |
| Northern Chestnut-tailed Antbird | Sciaphylax castanea | Zimmer's Antbird | Sciaphylax castanea | zimant1 |
| Grosbeak Starling | Scissirostrum dubium | Finch-billed Myna | Scissirostrum dubium | fibmyn2 |
| Grey-winged Francolin | Scleroptila afra | Gray-winged Francolin | Scleroptila afra | gywfra1 |
| Grey-throated Leaftosser | Sclerurus albigularis | Gray-throated Leaftosser | Sclerurus albigularis | grtlea1 |
| Tawny-throated Leaftosser | Sclerurus mexicanus | Middle American Leaftosser | Sclerurus mexicanus | tatlea1 |
| Dusky Leaftosser | Sclerurus obscurior | South American Leaftosser | Sclerurus obscurior | soalea1 |
| El Oro Tapaculo | Scytalopus robbinsi | Ecuadorian Tapaculo | Scytalopus robbinsi | ecutap1 |
| Narino Tapaculo | Scytalopus vicinior | Nariño Tapaculo | Scytalopus vicinior | nartap2 |
| Standardwing | Semioptera wallacii | Standardwing Bird-of-Paradise | Semioptera wallacii | walsta2 |
| Grey-lored Broadbill | Serilophus rubropygius | Gray-lored Broadbill | Serilophus rubropygius | sibbro2 |
| Atlantic Canary | Serinus canaria | Island Canary | Serinus canaria | comcan |
| Red-fronted Serin | Serinus pusillus | Fire-fronted Serin | Serinus pusillus | fifser1 |
| American Yellow Warbler | Setophaga aestiva | Northern Yellow Warbler | Setophaga aestiva | yelwar1 |
| Black-throated Grey Warbler | Setophaga nigrescens | Black-throated Gray Warbler | Setophaga nigrescens | btywar |
| Przevalski's Parrotbill | Suthora przewalskii | Rusty-throated Parrotbill | Suthora przewalskii | rutpar2 |
| Grey-hooded Parrotbill | Suthora zappeyi | Gray-hooded Parrotbill | Suthora zappeyi | gyhpar4 |
| Least Poorwill | Siphonorhis brewsteri | Least Pauraque | Siphonorhis brewsteri | leapau1 |
| Chinese Nuthatch | Sitta villosa | Snowy-browed Nuthatch | Sitta villosa | snbnut1 |
| Grey-headed Broadbill | Smithornis sharpei | Gray-headed Broadbill | Smithornis sharpei | gyhbro1 |
| Grey-tailed Piha | Snowornis subalaris | Gray-tailed Piha | Snowornis subalaris | gytpih1 |
| Bronze-winged Duck | Speculanas specularis | Spectacled Duck | Speculanas specularis | speduc2 |
| Grey-bellied Wren-Babbler | Spelaeornis reptatus | Gray-bellied Wren-Babbler | Spelaeornis reptatus | gybwrb1 |
| Grey Seedeater | Sporophila intermedia | Gray Seedeater | Sporophila intermedia | grysee1 |
| Scaly-feathered Weaver | Sporopipes squamifrons | Scaly Weaver | Sporopipes squamifrons | scawea1 |
| Grey-throated Babbler | Stachyris nigriceps | Gray-throated Babbler | Stachyris nigriceps | gytbab1 |
| Grey-headed Babbler | Stachyris poliocephala | Gray-headed Babbler | Stachyris poliocephala | gyhbab1 |
| Straw-backed Tanager | Stilpnia argyrofenges | Green-throated Tanager | Stilpnia argyrofenges | gnttan1 |
| Silver-backed Tanager | Stilpnia viridicollis | Silvery Tanager | Stilpnia viridicollis | siltan1 |
| Grey Currawong | Strepera versicolor | Gray Currawong | Strepera versicolor | grycur1 |
| Great Grey Owl | Strix nebulosa | Great Gray Owl | Strix nebulosa | grgowl |
| Common Starling | Sturnus vulgaris | European Starling | Sturnus vulgaris | eursta |
| Black Monarch | Symposiachrus axillaris | Fan-tailed Monarch | Symposiachrus axillaris | blamon1 |
| Moluccan Monarch | Symposiachrus bimaculatus | Moluccan Spectacled Monarch | Symposiachrus bimaculatus | molmon1 |
| Grey-bellied Spinetail | Synallaxis cinerascens | Gray-bellied Spinetail | Synallaxis cinerascens | gybspi1 |
| Maranon Spinetail | Synallaxis maranonica | Marañon Spinetail | Synallaxis maranonica | marspi3 |
| Planalto Foliage-gleaner | Syndactyla dimidiata | Russet-mantled Foliage-gleaner | Syndactyla dimidiata | rumfog1 |
| Chubut Steamer Duck | Tachyeres leucocephalus | White-headed Steamer-Duck | Tachyeres leucocephalus | whhstd1 |
| Fuegian Steamer Duck | Tachyeres pteneres | Flightless Steamer-Duck | Tachyeres pteneres | flistd1 |
| Black-billed Brushturkey | Talegalla fuscirostris | Yellow-legged Brushturkey | Talegalla fuscirostris | bkbbrt1 |
| Collared Brushturkey | Talegalla jobiensis | Red-legged Brushturkey | Talegalla jobiensis | bncbrt1 |
| Common Paradise Kingfisher | Tanysiptera galatea | Papuan Paradise-Kingfisher | Tanysiptera galatea | compak16 |
| Gorgeous Bushshrike | Telophorus viridis | Four-colored Bushshrike | Telophorus viridis | focbus2 |
| Grey-bellied Tesia | Tesia cyaniventer | Gray-bellied Tesia | Tesia cyaniventer | gybtes1 |
| Shy Albatross | Thalassarche cauta | White-capped Albatross | Thalassarche cauta | whcalb1 |
| Blackish-grey Antshrike | Thamnophilus nigrocinereus | Blackish-gray Antshrike | Thamnophilus nigrocinereus | blgant2 |
| Grey-breasted Seedsnipe | Thinocorus orbignyianus | Gray-breasted Seedsnipe | Thinocorus orbignyianus | gybsee1 |
| Blue-grey Tanager | Thraupis episcopus | Blue-gray Tanager | Thraupis episcopus | bugtan |
| Australian White Ibis | Threskiornis molucca | Australian Ibis | Threskiornis molucca | ausibi1 |
| Peruvian Treehunter | Thripadectes scrutator | Rufous-backed Treehunter | Thripadectes scrutator | rubtre1 |
| Sparkling-tailed Woodstar | Tilmatura dupontii | Sparkling-tailed Hummingbird | Tilmatura dupontii | spthum1 |
| Grey Tinamou | Tinamus tao | Gray Tinamou | Tinamus tao | grytin1 |
| Islet Kingfisher | Todiramphus colonus | Colonist Kingfisher | Todiramphus colonus | colkin17 |
| Yellow-lored Tody-Flycatcher | Todirostrum poliocephalum | Gray-headed Tody-Flycatcher | Todirostrum poliocephalum | gyhtof1 |
| Grey-crowned Flatbill | Tolmomyias poliocephalus | Gray-crowned Flatbill | Tolmomyias poliocephalus | gycfly1 |
| Slaty-headed Longbill | Toxorhamphus poliopterus | Slaty-chinned Longbill | Toxorhamphus poliopterus | slclon1 |
| Grey Thrasher | Toxostoma cinereum | Gray Thrasher | Toxostoma cinereum | grathr1 |
| Grey-fronted Green Pigeon | Treron affinis | Gray-fronted Green-Pigeon | Treron affinis | pomgrp2 |
| Grey-cheeked Green Pigeon | Treron griseicauda | Gray-cheeked Green-Pigeon | Treron griseicauda | gycpig1 |
| Grey-tailed Tattler | Tringa brevipes | Gray-tailed Tattler | Tringa brevipes | gyttat1 |
| Willet | Tringa semipalmata | Saltmarsh Willet | Tringa semipalmata | willet2 |
| Blue-mantled Crested Flycatcher | Trochocercus cyanomelas | African Crested Flycatcher | Trochocercus cyanomelas | afcfly1 |
| Gartered Trogon | Trogon caligatus | Gartered Violaceous Trogon | Trogon caligatus | gartro1 |
| Choco Trogon | Trogon comptus | Blue-tailed Trogon | Trogon comptus | buttro1 |
| Amazonian Trogon | Trogon ramonianus | Amazonian Violaceous Trogon | Trogon ramonianus | viotro3 |
| Guianan Trogon | Trogon violaceus | Guianan Violaceous Trogon | Trogon violaceus | viotro2 |
| Green-legged Partridge | Tropicoperdix chloropus | Scaly-breasted Partridge | Tropicoperdix chloropus | scbpar1 |
| Hinde's Babbler | Turdoides hindei | Hinde's Pied Babbler | Turdoides hindei | hipbab1 |
| White-necked Thrush | Turdus albicollis | Rufous-flanked Thrush | Turdus albicollis | whnthr2 |
| Grey-winged Blackbird | Turdus boulboul | Gray-winged Blackbird | Turdus boulboul | gywbla1 |
| Grey-sided Thrush | Turdus feae | Gray-sided Thrush | Turdus feae | gysthr1 |
| Grey-backed Thrush | Turdus hortulorum | Gray-backed Thrush | Turdus hortulorum | gybthr1 |
| Maranon Thrush | Turdus maranonicus | Marañon Thrush | Turdus maranonicus | marthr2 |
| Common Blackbird | Turdus merula | Eurasian Blackbird | Turdus merula | eurbla |
| Rufous-collared Thrush | Turdus rufitorques | Rufous-collared Robin | Turdus rufitorques | rucrob1 |
| Rufous-backed Thrush | Turdus rufopalliatus | Rufous-backed Robin | Turdus rufopalliatus | rubrob |
| Common Buttonquail | Turnix sylvaticus | Small Buttonquail | Turnix sylvaticus | smabut2 |
| Grey Kingbird | Tyrannus dominicensis | Gray Kingbird | Tyrannus dominicensis | grykin |
| Eastern Grass Owl | Tyto longimembris | Australasian Grass-Owl | Tyto longimembris | ausgro1 |
| Australian Masked Owl | Tyto novaehollandiae | Australasian Masked-Owl | Tyto novaehollandiae | ausmao7 |
| Blue Waxbill | Uraeginthus angolensis | Southern Cordonbleu | Uraeginthus angolensis | bubcor1 |
| Przevalski's Finch | Urocynchramus pylzowi | Przevalski's Pinktail | Urocynchramus pylzowi | przros1 |
| Papuan Hawk-Owl | Uroglaux dimorpha | Papuan Owl | Uroglaux dimorpha | paphao1 |
| Grey-headed Lapwing | Vanellus cinereus | Gray-headed Lapwing | Vanellus cinereus | gyhlap1 |
| African Wattled Lapwing | Vanellus senegallus | Wattled Lapwing | Vanellus senegallus | watlap1 |
| Zambezi Indigobird | Vidua codringtoni | Green Indigobird | Vidua codringtoni | greind1 |
| Long-tailed Paradise Whydah | Vidua paradisaea | Eastern Paradise-Whydah | Vidua paradisaea | eapwhy1 |
| Warbling Vireo | Vireo gilvus | Eastern Warbling Vireo | Vireo gilvus | eawvir1 |
| Grey Vireo | Vireo vicinior | Gray Vireo | Vireo vicinior | gryvir |
| Grey-crowned Tetraka | Xanthomixis cinereiceps | Gray-crowned Tetraka | Xanthomixis cinereiceps | gyctet1 |
| Double-banded Greytail | Xenerpestes minlosi | Double-banded Graytail | Xenerpestes minlosi | dobgra1 |
| Equatorial Greytail | Xenerpestes singularis | Equatorial Graytail | Xenerpestes singularis | equgra1 |
| New Zealand Rockwren | Xenicus gilviventris | South Island Wren | Xenicus gilviventris | soiwre1 |
| Speckled Antshrike | Xenornis setifrons | Spiny-faced Antshrike | Xenornis setifrons | spfant1 |
| Grey-capped Pygmy Woodpecker | Yungipicus canicapillus | Gray-capped Pygmy Woodpecker | Yungipicus canicapillus | gycwoo1 |
| Reunion Grey White-eye | Zosterops borbonicus | Reunion Gray White-eye | Zosterops borbonicus | maswhe2 |
| Broad-ringed White-eye | Zosterops eurycricotus | Kilimanjaro White-eye | Zosterops eurycricotus | brrwhe8 |
| Canary White-eye | Zosterops luteus | Australian Yellow White-eye | Zosterops luteus | ayweye3 |
| Mauritius Grey White-eye | Zosterops mauritianus | Mauritius Gray White-eye | Zosterops mauritianus | maswhe3 |
| Papuan White-eye | Zosterops novaeguineae | New Guinea White-eye | Zosterops novaeguineae | ngweye1 |
| Olive-colored White-eye | Zosterops oleagineus | Yap White-eye | Zosterops oleagineus | yapwhe1 |
| Grey-brown White-eye | Zosterops ponapensis | Pohnpei White-eye | Zosterops ponapensis | pohwhe1 |
| Citrine White-eye | Zosterops semperi | Caroline Islands White-eye | Zosterops semperi | ciweye1 |

### cached_species_code_review

| BirdNET common name | BirdNET scientific name | eBird common name / candidate | eBird scientific name | eBird code |
| --- | --- | --- | --- | --- |
| House Swift | Apus nipalensis | Little Swift (House) | Apus affinis [nipalensis Group] | houswi1 |
| Bob-tailed Weaver | Brachycope anomala | Bob-tailed Weaver | Euplectes anomalus | botwea1 |
| Brown-rumped Bunting | Emberiza affinis | Brown-rumped Bunting | Fringillaria affinis | brrbun1 |
| Yellow-breasted Bunting | Emberiza aureola | Yellow-breasted Bunting | Schoeniclus aureolus | yebbun |
| Red-headed Bunting | Emberiza bruniceps | Red-headed Bunting | Melophus bruniceps | rehbun1 |
| Cabanis's Bunting | Emberiza cabanisi | Cabanis's Bunting | Fringillaria cabanisi | cabbun1 |
| Cape Bunting | Emberiza capensis | Cape Bunting | Fringillaria capensis | capbun1 |
| Yellow-browed Bunting | Emberiza chrysophrys | Yellow-browed Bunting | Schoeniclus chrysophrys | yebbun1 |
| Yellow-throated Bunting | Emberiza elegans | Yellow-throated Bunting | Schoeniclus elegans | yetbun1 |
| Golden-breasted Bunting | Emberiza flaviventris | Golden-breasted Bunting | Fringillaria flaviventris | gobbun1 |
| Gosling's Bunting | Emberiza goslingi | Gosling's Bunting | Fringillaria goslingi | gosbun1 |
| Lark-like Bunting | Emberiza impetuani | Lark-like Bunting | Fringillaria impetuani | lalbun1 |
| Crested Bunting | Emberiza lathami | Crested Bunting | Melophus lathami | crebun1 |
| Black-headed Bunting | Emberiza melanocephala | Black-headed Bunting | Melophus melanocephalus | blhbun1 |
| Pallas's Reed Bunting | Emberiza pallasi | Pallas's Bunting | Schoeniclus pallasi | palbun |
| Masked Bunting | Emberiza personata | Masked Bunting | Schoeniclus personatus | bkfbun2 |
| Somali Bunting | Emberiza poliopleura | Somali Bunting | Fringillaria poliopleura | sombun1 |
| Little Bunting | Emberiza pusilla | Little Bunting | Schoeniclus pusillus | litbun |
| Rustic Bunting | Emberiza rustica | Rustic Bunting | Schoeniclus rusticus | rusbun |
| Chestnut Bunting | Emberiza rutila | Chestnut Bunting | Schoeniclus rutilus | chebun1 |
| House Bunting | Emberiza sahari | House Bunting | Fringillaria sahari | houbun3 |
| Common Reed Bunting | Emberiza schoeniclus | Reed Bunting | Schoeniclus schoeniclus | reebun |
| Slaty Bunting | Emberiza siemsseni | Slaty Bunting | Schoeniclus siemsseni | slabun1 |
| Black-faced Bunting | Emberiza spodocephala | Black-faced Bunting | Schoeniclus spodocephalus | bkfbun1 |
| Striolated Bunting | Emberiza striolata | Striolated Bunting | Fringillaria striolata | houbun2 |
| Yellow Bunting | Emberiza sulphurata | Yellow Bunting | Schoeniclus sulphuratus | yelbun1 |
| Cinnamon-breasted Bunting | Emberiza tahapisi | Cinnamon-breasted Bunting | Fringillaria tahapisi | cibbun1 |
| Tristram's Bunting | Emberiza tristrami | Tristram's Bunting | Schoeniclus tristrami | tribun1 |
| Grey Bunting | Emberiza variabilis | Gray Bunting | Schoeniclus variabilis | grybun |
| Ochre-rumped Bunting | Emberiza yessoensis | Ochre-rumped Bunting | Schoeniclus yessoensis | ocrbun1 |
| Kalinowski's Chat-Tyrant | Silvicultrix spodionota | Crowned Chat-Tyrant (Kalinowski's) | Silvicultrix frontalis spodionota/boliviana | crocht3 |
| Marbled Honeyeater | Pycnopygius cinereus | Marbled Honeyeater | Pinarostola cinerea | marhon1 |
| Western Hemispingus | Sphenopsis ochracea | Black-eared Hemispingus (Western) | Sphenopsis melanotis ochracea | bkehem3 |
| Piura Hemispingus | Sphenopsis piurae | Black-eared Hemispingus (Piura) | Sphenopsis melanotis piurae/macrophrys | bkehem1 |
| Timberline Wren | Thryorchilus browni | Timberline Wren | Troglodytes browni | timwre1 |
| Winter Wren | Troglodytes hiemalis | Winter Wren | Nannus hiemalis | winwre3 |
| Pacific Wren | Troglodytes pacificus | Pacific Wren | Nannus pacificus | pacwre1 |
| Eurasian Wren | Troglodytes troglodytes | Eurasian Wren | Nannus troglodytes | winwre4 |
| Sulawesi Masked Owl | Tyto rosenbergii | Eastern Barn Owl (Sulawesi) | Tyto javanica rosenbergii/pelengensis | sulowl1 |

### common_name_only_review

| BirdNET common name | BirdNET scientific name | eBird common name / candidate | eBird scientific name | eBird code |
| --- | --- | --- | --- | --- |
| Green-winged Teal | Anas carolinensis | Green-winged Teal | Anas crecca | gnwtea |
| Blue Crane | Anthropoides paradiseus | Blue Crane | Grus paradisea | blucra2 |
| Demoiselle Crane | Anthropoides virgo | Demoiselle Crane | Grus virgo | demcra1 |
| Black-banded Crake | Anurolimnas fasciatus | Black-banded Crake | Rufirallus fasciatus | blbcra1 |
| Fan-tailed Warbler | Basileuterus lachrymosus | Fan-tailed Warbler | Euthlypis lachrymosa | fatwar |
| Scarlet-rumped Cacique | Cacicus microrhynchus | Scarlet-rumped Cacique | Cacicus uropygialis | scrcac1 |
| Little Ringed Plover | Charadrius dubius | Little Ringed Plover | Thinornis dubius | lirplo |
| Forbes's Plover | Charadrius forbesi | Forbes's Plover | Thinornis forbesi | forplo1 |
| Long-billed Plover | Charadrius placidus | Long-billed Plover | Thinornis placidus | lobplo1 |
| Three-banded Plover | Charadrius tricollaris | Three-banded Plover | Thinornis tricollaris | thbplo1 |
| Duchess Lorikeet | Charmosynoides margarethae | Duchess Lorikeet | Vini margarethae | duclor1 |
| Hooded Grosbeak | Coccothraustes abeillei | Hooded Grosbeak | Hesperiphona abeillei | hoogro1 |
| Evening Grosbeak | Coccothraustes vespertinus | Evening Grosbeak | Hesperiphona vespertina | evegro |
| Green Jay | Cyanocorax luxuosus | Green Jay | Cyanocorax yncas | grnjay |
| Thick-billed Flowerpecker | Dicaeum agile | Thick-billed Flowerpecker | Pachyglossa agilis | thbflo1 |
| Yellow-vented Flowerpecker | Dicaeum chrysorrheum | Yellow-vented Flowerpecker | Pachyglossa chrysorrhea | yevflo1 |
| Yellow-bellied Flowerpecker | Dicaeum melanozanthum | Yellow-bellied Flowerpecker | Pachyglossa melanozantha | yebflo1 |
| Whiskered Flowerpecker | Dicaeum proprium | Whiskered Flowerpecker | Pachyglossa propria | whiflo1 |
| Cloven-feathered Dove | Drepanoptila holosericea | Cloven-feathered Dove | Ptilinopus holosericeus | clfdov1 |
| Red-stained Woodpecker | Dryobates affinis | Red-stained Woodpecker | Veniliornis affinis | reswoo1 |
| White-headed Woodpecker | Dryobates albolarvatus | White-headed Woodpecker | Leuconotopicus albolarvatus | whhwoo |
| Arizona Woodpecker | Dryobates arizonae | Arizona Woodpecker | Leuconotopicus arizonae | ariwoo |
| Red-cockaded Woodpecker | Dryobates borealis | Red-cockaded Woodpecker | Leuconotopicus borealis | recwoo |
| Scarlet-backed Woodpecker | Dryobates callonotus | Scarlet-backed Woodpecker | Veniliornis callonotus | scbwoo3 |
| Golden-collared Woodpecker | Dryobates cassini | Golden-collared Woodpecker | Veniliornis cassini | gocwoo2 |
| Yellow-vented Woodpecker | Dryobates dignus | Yellow-vented Woodpecker | Veniliornis dignus | yevwoo1 |
| Dot-fronted Woodpecker | Dryobates frontalis | Dot-fronted Woodpecker | Veniliornis frontalis | dofwoo1 |
| Smoky-brown Woodpecker | Dryobates fumigatus | Smoky-brown Woodpecker | Leuconotopicus fumigatus | smbwoo1 |
| Red-rumped Woodpecker | Dryobates kirkii | Red-rumped Woodpecker | Veniliornis kirkii | rerwoo1 |
| Striped Woodpecker | Dryobates lignarius | Striped Woodpecker | Veniliornis lignarius | strwoo6 |
| Yellow-eared Woodpecker | Dryobates maculifrons | Yellow-eared Woodpecker | Veniliornis maculifrons | yeewoo1 |
| Checkered Woodpecker | Dryobates mixtus | Checkered Woodpecker | Veniliornis mixtus | chewoo3 |
| Bar-bellied Woodpecker | Dryobates nigriceps | Bar-bellied Woodpecker | Veniliornis nigriceps | babwoo2 |
| Little Woodpecker | Dryobates passerinus | Little Woodpecker | Veniliornis passerinus | litwoo2 |
| Blood-colored Woodpecker | Dryobates sanguineus | Blood-colored Woodpecker | Veniliornis sanguineus | blcwoo3 |
| White-spotted Woodpecker | Dryobates spilogaster | White-spotted Woodpecker | Veniliornis spilogaster | whswoo2 |
| Strickland's Woodpecker | Dryobates stricklandi | Strickland's Woodpecker | Leuconotopicus stricklandi | strwoo |
| Hairy Woodpecker | Dryobates villosus | Hairy Woodpecker | Leuconotopicus villosus | haiwoo |
| Plum-headed Finch | Emblema modesta | Plum-headed Finch | Emblema modestum | plhfin1 |
| Musk Lorikeet | Glossopsitta concinna | Musk Lorikeet | Trichoglossus concinnus | muslor1 |
| Spot-tailed Nightjar | Hydropsalis maculicaudus | Spot-tailed Nightjar | Antiurus maculicaudus | sptnig1 |
| Red-and-white Crake | Laterallus leucopyrrhus | Red-and-white Crake | Rufirallus leucopyrrhus | rawcra1 |
| Dot-winged Crake | Laterallus spilopterus | Dot-winged Crake | Laterallus spiloptera | dowcra1 |
| Rufous-faced Crake | Laterallus xenopterus | Rufous-faced Crake | Rufirallus xenopterus | rufcra1 |
| Long-trained Nightjar | Macropsalis forcipata | Long-trained Nightjar | Hydropsalis forcipata | lotnig2 |
| Cryptic Honeyeater | Microptilotis imitatrix | Cryptic Honeyeater | Meliphaga imitatrix | grahon5 |
| Serra do Mar Tyrant-Manakin | Neopelma chrysolophum | Serra do Mar Tyrant-Manakin | Protopelma chrysolophum | sdmman1 |
| Wedge-tailed Sabrewing | Pampa pampa | Wedge-tailed Sabrewing | Pampa curvipennis | wetsab1 |
| Purple-crowned Lorikeet | Parvipsitta porphyrocephala | Purple-crowned Lorikeet | Psitteuteles porphyrocephalus | puclor1 |
| Little Lorikeet | Parvipsitta pusilla | Little Lorikeet | Psitteuteles pusillus | litlor1 |
| Hepatic Tanager | Piranga hepatica | Hepatic Tanager | Piranga flava | heptan |
| Chestnut Wattle-eye | Platysteira castanea | Chestnut Wattle-eye | Dyaphorophyia castanea | chweye1 |
| Olive-backed Flowerpecker | Prionochilus olivaceus | Olive-backed Flowerpecker | Pachyglossa olivacea | olbflo1 |
| Dusky Lory | Pseudeos fuscata | Dusky Lory | Chalcopsitta fuscata | duslor1 |
| Vermilion Flycatcher | Pyrocephalus obscurus | Vermilion Flycatcher | Pyrocephalus rubinus | verfly |
| Yellow-cheeked Lorikeet | Saudareos meyeri | Yellow-cheeked Lorikeet | Trichoglossus meyeri | yaglor2 |
| Tschudi's Nightjar | Systellura decussata | Tschudi's Nightjar | Quechuavis decussata | bawnig3 |
| Black-fronted White-eye | Zosterops chrysolaemus | Black-fronted White-eye | Zosterops minor | bfweye1 |

### unresolved

| BirdNET common name | BirdNET scientific name | eBird common name / candidate | eBird scientific name | eBird code |
| --- | --- | --- | --- | --- |
| Acanthis cabaret | Acanthis cabaret | — | — | — |
| Acanthis hornemanni | Acanthis hornemanni | — | — | — |
| White-breasted Hawk | Accipiter chionogaster | — | — | — |
| Rufous-thighed Hawk | Accipiter erythronemius | — | — | — |
| Accipiter toussenelii | Accipiter toussenelii | — | — | — |
| Plain-breasted Hawk | Accipiter ventralis | — | — | — |
| Acrocephalus baeticatus | Acrocephalus baeticatus | — | — | — |
| Black-browed Bushtit | Aegithalos bonvaloti | — | — | — |
| Burmese Bushtit | Aegithalos sharpei | — | — | — |
| Aerodramus germani | Aerodramus germani | — | — | — |
| Aethopyga jefferyi | Aethopyga jefferyi | — | — | — |
| Arfak Catbird | Ailuroedus arfakianus | — | — | — |
| Black-capped Catbird | Ailuroedus melanocephalus | — | — | — |
| Athi Short-toed Lark | Alaudala athensis | — | — | — |
| Amazona guatemalae | Amazona guatemalae | — | — | — |
| Anthus lutescens | Anthus lutescens | — | — | — |
| Brown-tailed Apalis | Apalis flavocincta | — | — | — |
| Red-throated Parakeet | Psittacara rubritorquis | — | — | — |
| Asthenes sclateri | Asthenes sclateri | — | — | — |
| Merida Brushfinch | Atlapetes meridae | — | — | — |
| Black-throated Toucanet | Aulacorhynchus atrogularis | — | — | — |
| Blue-throated Toucanet | Aulacorhynchus caeruleogularis | — | — | — |
| Wagler's Toucanet | Aulacorhynchus wagleri | — | — | — |
| Bubo coromandus | Bubo coromandus | — | — | — |
| Bubo nipalensis | Bubo nipalensis | — | — | — |
| Bubo sumatranus | Bubo sumatranus | — | — | — |
| Bubo vosseleri | Bubo vosseleri | — | — | — |
| Burhinus bistriatus | Burhinus bistriatus | — | — | — |
| Burhinus superciliaris | Burhinus superciliaris | — | — | — |
| Cacicus leucoramphus | Cacicus leucoramphus | — | — | — |
| Calendulauda alopex | Calendulauda alopex | — | — | — |
| Grey-backed Camaroptera | Camaroptera brevicaudata | — | — | — |
| Little Spotted Woodpecker | Campethera cailliautii | — | — | — |
| Caprimulgus nigriscapularis | Caprimulgus nigriscapularis | — | — | — |
| Celeus grammicus | Celeus grammicus | — | — | — |
| Erythropygia coryphoeus | Erythropygia coryphoeus | — | — | — |
| Agulhas Long-billed Lark | Certhilauda brevirostris | — | — | — |
| Charadrius alticola | Charadrius alticola | — | — | — |
| Charadrius bicinctus | Charadrius bicinctus | — | — | — |
| Charadrius collaris | Charadrius collaris | — | — | — |
| Charadrius falklandicus | Charadrius falklandicus | — | — | — |
| Charadrius javanicus | Charadrius javanicus | — | — | — |
| Charadrius marginatus | Charadrius marginatus | — | — | — |
| Elseyornis melanops | Elseyornis melanops | — | — | — |
| Charadrius mongolus | Charadrius mongolus | — | — | — |
| Charadrius montanus | Charadrius montanus | — | — | — |
| Charadrius nivosus | Charadrius nivosus | — | — | — |
| Charadrius pallidus | Charadrius pallidus | — | — | — |
| Charadrius pecuarius | Charadrius pecuarius | — | — | — |
| Charadrius peronii | Charadrius peronii | — | — | — |
| Charadrius ruficapillus | Charadrius ruficapillus | — | — | — |
| Charadrius thoracicus | Charadrius thoracicus | — | — | — |
| Charadrius veredus | Charadrius veredus | — | — | — |
| Charadrius wilsonia | Charadrius wilsonia | — | — | — |
| Chloropsis lazulina | Chloropsis lazulina | — | — | — |
| Cisticola emini | Cisticola emini | — | — | — |
| Bronze-winged Woodpecker | Colaptes aeruginosus | — | — | — |
| Variable Shrikethrush | Colluricincla fortis | — | — | — |
| Rufous Shrikethrush | Colluricincla rufogaster | — | — | — |
| Sepik-Ramu Shrikethrush | Colluricincla tappenbecki | — | — | — |
| Indian Jungle Crow | Corvus culminatus | — | — | — |
| Eastern Jungle Crow | Corvus levaillantii | — | — | — |
| Cossypha ansorgei | Cossypha ansorgei | — | — | — |
| Curruca althaea | Curruca althaea | — | — | — |
| Curruca minula | Curruca minula | — | — | — |
| Cyanoderma ambiguum | Cyanoderma ambiguum | — | — | — |
| Blue-fronted Fig Parrot | Cyclopsitta gulielmitertii | — | — | — |
| Dicrurus atactus | Dicrurus atactus | — | — | — |
| Dicrurus divaricatus | Dicrurus divaricatus | — | — | — |
| Dicrurus occidentalis | Dicrurus occidentalis | — | — | — |
| Dimorphic Egret | Egretta dimorpha | — | — | — |
| Chilean Elaenia | Elaenia chilensis | — | — | — |
| Empidonax occidentalis | Empidonax occidentalis | — | — | — |
| Maghreb Lark | Galerida macrorhyncha | — | — | — |
| Chiriqui Yellowthroat | Geothlypis chiriquensis | — | — | — |
| Northern Pygmy Owl | Glaucidium californicum | — | — | — |
| Guatemalan Pygmy Owl | Glaucidium cobanense | — | — | — |
| Baja Pygmy Owl | Glaucidium hoskinsii | — | — | — |
| Haliaeetus humilis | Haliaeetus humilis | — | — | — |
| Haliaeetus ichthyaetus | Haliaeetus ichthyaetus | — | — | — |
| Serra do Lontras Treehunter | Heliobletus sp.nov.Lontras | — | — | — |
| White-backed Stilt | Himantopus melanurus | — | — | — |
| Horornis vulcanius | Horornis vulcanius | — | — | — |
| Hylexetastes brigidai | Hylexetastes brigidai | — | — | — |
| Indicator conirostris | Indicator conirostris | — | — | — |
| White-browed Hemispingus | Kleinothraupis auricularis | — | — | — |
| Miombo Blue-eared Starling | Lamprotornis elisabeth | — | — | — |
| Azuero Dove | Leptotila battyi | — | — | — |
| Antarctic Shag | Leucocarbo bransfieldensis | — | — | — |
| Lichmera limbata | Lichmera limbata | — | — | — |
| Lophochroa leadbeateri | Lophochroa leadbeateri | — | — | — |
| Luscinia sibilans | Luscinia sibilans | — | — | — |
| Megascops vermiculatus | Megascops vermiculatus | — | — | — |
| Melaenornis infuscatus | Melaenornis infuscatus | — | — | — |
| Melaenornis mariquensis | Melaenornis mariquensis | — | — | — |
| Melaenornis microrhynchus | Melaenornis microrhynchus | — | — | — |
| Velasquez's Woodpecker | Melanerpes santacruzi | — | — | — |
| Yellow-billed Kite | Milvus aegyptius | — | — | — |
| Mirafra cantillans | Mirafra cantillans | — | — | — |
| Monarcha erythrostictus | Monarcha erythrostictus | — | — | — |
| Muscicapa boehmi | Muscicapa boehmi | — | — | — |
| Muscicapa tessmanni | Muscicapa tessmanni | — | — | — |
| Muscicapa ussheri | Muscicapa ussheri | — | — | — |
| Myiornis sp.nov.Maranhao_Piaui | Myiornis sp.nov.Maranhao_Piaui | — | — | — |
| Roraiman Warbler | Myiothlypis roraimae | — | — | — |
| Silvery-flanked Antwren | Myrmotherula luctuosa | — | — | — |
| Phaeomyias murina | Phaeomyias murina | — | — | — |
| Chaco Puffbird | Nystalus striatipectus | — | — | — |
| Onychorhynchus mexicanus | Onychorhynchus mexicanus | — | — | — |
| Torotoroka Scops Owl | Otus madagascariensis | — | — | — |
| Western Whistler | Pachycephala fuliginosa | — | — | — |
| Yellow-cheeked Becard | Pachyramphus xanthogenys | — | — | — |
| Pampa excellens | Pampa excellens | — | — | — |
| Pandion cristatus | Pandion cristatus | — | — | — |
| Sinosuthora webbiana | Sinosuthora webbiana | — | — | — |
| Parus minor | Parus minor | — | — | — |
| Thick-billed Fox Sparrow | Passerella megarhyncha | — | — | — |
| Slate-colored Fox Sparrow | Passerella schistacea | — | — | — |
| Sooty Fox Sparrow | Passerella unalaschcensis | — | — | — |
| Percnostola fortis | Percnostola fortis | — | — | — |
| Percnostola goeldii | Percnostola goeldii | — | — | — |
| Percnostola immaculata | Percnostola immaculata | — | — | — |
| Percnostola melanoceps | Percnostola melanoceps | — | — | — |
| Percnostola zeledoni | Percnostola zeledoni | — | — | — |
| White-breasted Cormorant | Phalacrocorax lucidus | — | — | — |
| New Guinea Friarbird | Philemon novaeguineae | — | — | — |
| Hornbill Friarbird | Philemon yorki | — | — | — |
| Placid Greenbul | Phyllastrephus placidus | — | — | — |
| Phylloscartes difficilis | Phylloscartes difficilis | — | — | — |
| Phylloscartes paulista | Phylloscartes paulista | — | — | — |
| White-capped Parrot | Pionus seniloides | — | — | — |
| Tooth-billed Tanager | Piranga lutea | — | — | — |
| Pnoepyga mutica | Pnoepyga mutica | — | — | — |
| Black-faced Prinia | Prinia melanops | — | — | — |
| White-bellied Whipbird | Psophodes leucogaster | — | — | — |
| Brown-mandibled Aracari | Pteroglossus mariae | — | — | — |
| Stripe-billed Aracari | Pteroglossus sanguineus | — | — | — |
| Pteruthius annamensis | Pteruthius annamensis | — | — | — |
| Pteruthius ripleyi | Pteruthius ripleyi | — | — | — |
| Scarlet-breasted Fruit Dove | Ptilinopus bernsteinii | — | — | — |
| Oberholser's Fruit Dove | Ptilinopus epius | — | — | — |
| Red-eared Fruit Dove | Ptilinopus fischeri | — | — | — |
| Jambu Fruit Dove | Ptilinopus jambu | — | — | — |
| Black-chinned Fruit Dove | Ptilinopus leclancheri | — | — | — |
| Wompoo Fruit Dove | Ptilinopus magnificus | — | — | — |
| Sula Fruit Dove | Ptilinopus mangoliensis | — | — | — |
| Flame-breasted Fruit Dove | Ptilinopus marchei | — | — | — |
| Cream-breasted Fruit Dove | Ptilinopus merrilli | — | — | — |
| Yellow-breasted Fruit Dove | Ptilinopus occipitalis | — | — | — |
| Banggai Fruit Dove | Ptilinopus subgularis | — | — | — |
| Dodson's Bulbul | Pycnonotus dodsoni | — | — | — |
| Somali Bulbul | Pycnonotus somaliensis | — | — | — |
| Dark-capped Bulbul | Pycnonotus tricolor | — | — | — |
| Citron-throated Toucan | Ramphastos citreolaemus | — | — | — |
| Lemon-rumped Tanager | Ramphocelus icteronotus | — | — | — |
| African Crimson-winged Finch | Rhodopechys alienus | — | — | — |
| Saudareos ornatus | Saudareos ornatus | — | — | — |
| Madagascar Stonechat | Saxicola sibilla | — | — | — |
| Rubeho Warbler | Scepomycter rubehoensis | — | — | — |
| Perplexing Scrubwren | Sericornis virgatus | — | — | — |
| Serpophaga munda | Serpophaga munda | — | — | — |
| Audubon's Warbler | Setophaga auduboni | — | — | — |
| Spermestes nigriceps | Spermestes nigriceps | — | — | — |
| Sporophila murallae | Sporophila murallae | — | — | — |
| Maghreb Owl | Strix mauritanica | — | — | — |
| Telophorus quadricolor | Telophorus quadricolor | — | — | — |
| Cabot's Tern | Thalasseus acuflavidus | — | — | — |
| Thripophaga berlepschi | Thripophaga berlepschi | — | — | — |
| Usambiro Barbet | Trachyphonus usambiro | — | — | — |
| Ryukyu Green Pigeon | Treron permagnus | — | — | — |
| Lesser Sooty Owl | Tyto multipunctata | — | — | — |
| Moluccan Masked Owl | Tyto sororcula | — | — | — |
| African Hoopoe | Upupa africana | — | — | — |
| Providencia Vireo | Vireo approximans | — | — | — |
| Xiphorhynchus chunchotambo | Xiphorhynchus chunchotambo | — | — | — |
| Loja Tyrannulet | Zimmerius flavidifrons | — | — | — |
