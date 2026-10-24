# Experimental wingbeat detector

The built-in wingbeat detector marks possible wingbeats as `WING` for listening review. These candidates appear in review files, not eBird upload files, and are not species identifications.

**False positives are still very common.** Bats, rain, machinery, and other brief, repeating sounds can trigger it, and some actual wingbeats may be missed.

## Development

This is a rule-based screening detector, not a trained machine learning classifier. The detector has been developed and evaluated using wingbeat recordings sourced from xeno-canto and the Macaulay Library, as well as FSD50K recordings of potential false positives such as insects, rain, tools, and mechanical ticking.

### What triggers a WING detection?

The detector looks for repeated sound pulses in overlapping 1-, 1.5-, and 2-second listening windows. A sample must contain at least one second of audio, and a window must meet these requirements:

- **Several distinct pulses:** usually at least four, with repetition searched at roughly 2–20 pulses per second.
- **Noticeable loudness changes:** the quieter envelope level must be at least 25% below the louder level.
- **A repeating pattern:** normally a correlation score of at least 0.60 at one pulse period and 0.35 at two periods. Less regular pulses can qualify when other acoustic evidence is stronger.
- **Supporting frequency content:** either broadband flapping-like pulses across 150–3,000 Hz, synchronized in at least three frequency bands, or pulses associated with a spectral feature in the 700–9,500 Hz search range and nearby noise that rises and falls with them. Additional checks assess low-frequency support, noise strength, bandwidth, and spectral shape. One upper-frequency detection route requires at least six pulses.
- **Enough measurable signal:** the internal peak-envelope value must reach 0.0001. This is a processing threshold, not a microphone loudness or decibel requirement.

A single qualifying window triggers a detection; overlapping detections are merged. A bird call, species identification, or wing whistle is not required.

These are provisional screening thresholds, not a calibrated classifier. The reported periodicity score measures pulse repetition, not the probability that a sound is a wingbeat. **WING means “possible wingbeats—manual review required.”** Other repetitive sounds can meet these conditions.

## Source recordings for development and evaluation

**Macaulay Library.** Wingbeat recordings: Cornell Lab of Ornithology | Macaulay Library. Individual recordings are cited by species, recordist, and linked catalog number—for example: Mallard by Sławomir Karpicki; Cornell Lab of Ornithology | Macaulay Library ([ML645008811](https://macaulaylibrary.org/asset/645008811)). The [accompanying recording list](docs/wingbeat-recording-sources.md) provides citations for all 20 pilot recordings.

**xeno-canto.** Wingbeat recordings: [xeno-canto](https://xeno-canto.org/). Individual recordings are identified by recordist and linked XC catalog number, with the applicable license recorded in the source catalog.

**FSD50K.** Environmental-sound recordings: Fonseca, E., Favory, X., Pons, J., Font, F., & Serra, X. (2020). *FSD50K* (Version 1.0) [Data set]. Zenodo. [doi:10.5281/zenodo.4060432](https://doi.org/10.5281/zenodo.4060432).

**FSD50K reference publication.** Fonseca, E., Favory, X., Pons, J., Font, F., & Serra, X. (2022). FSD50K: An open dataset of human-labeled sound events. *IEEE/ACM Transactions on Audio, Speech, and Language Processing, 30*, 829–852.

## Further reading

- [NFC Tools installation and usage](README.md)
- [Wingbeat research methods and limitations](docs/wingbeat-research-audit.md)
- [October 16 waterfowl evaluation](docs/evaluations/wingbeat-waterfowl-2026-10-16/release-report.md)
- [Optional wingbeat research data and restore instructions](research/archive/2026-09-wingbeat-handoff/README.md)
