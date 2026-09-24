# WING research instrumentation feature dictionary

This sidecar instrumentation is designed to leave the production WING detector unchanged. Each two-second window records the production decision and a larger set of diagnostic measurements for later comparison of confirmed bird wingbeats with hard negatives.

## Production WING measurements retained

- `wing_spectral_flatness`: median spectral flatness of loud frames in 150–3000 Hz.
- `wing_modulation`: 10th-to-90th percentile envelope contrast.
- `wing_periodicity`: autocorrelation at the selected repetition lag.
- `wing_repeat_periodicity`: autocorrelation at twice the selected lag.
- `wing_pulse_count`: current distinct-pulse count.
- `wing_peak_envelope`: current envelope peak.
- `wing_coherent_bands`: current count of pulse bands passing synchrony/repetition/modulation gates.
- `wing_band_energy_fraction`: fraction of frame energy in the 150–3000 Hz analysis band.
- `acc_*`: all current tonal-accompaniment measurements for the four search bands: periodicity, repeat periodicity, modulation, noise coherence, noise contrast, noise ratio, ridge share, residual bins, pulse count, peak envelope, and noise-center frequency.
- `current_detect`, `current_score`, `current_route`, and gate-failure fields record the current WING result and why each research window did or did not satisfy the existing rules.

## Added temporal measurements

- `best_lag_frames`, `beat_rate_hz`, `beat_period_ms`.
- `pulse_times_sec`.
- `ipi_mean_ms`, `ipi_sd_ms`, `ipi_cv`: inter-pulse interval statistics.
- `ipi_npvi`: normalized pairwise variability index of successive intervals.
- `pulse_amp_cv`: cycle-to-cycle amplitude variability.
- `pulse_fwhm_ms_median`, `pulse_attack_ms_median`, `pulse_decay_ms_median`, `pulse_attack_decay_ratio`.

These are research variables only. IOI/interval variation and nPVI are established ways to quantify acoustic rhythm and distinguish isochrony from variable temporal patterns.

## Added cross-frequency timing measurements

For each of WING's four existing broadband pulse bands, the scanner records:

- continuous modulation, coherence, and repetition values;
- the lag in milliseconds that maximizes synchrony with the full-band envelope within ±50 ms;
- that maximum correlation;
- `band_sync_lag_spread_ms`, the spread of the four best lags.

The production detector currently reduces this information to a coherent-band count. The continuous measurements preserve the information needed to test whether true wing strokes are more nearly simultaneous across frequency than calls, machinery, footsteps, and other confounders.

## Added impulse and waveform measurements

- `rms`, `peak_abs`, `crest_factor`.
- `waveform_kurtosis`.
- `zero_cross_rate`.
- `pulse_biphasic_balance_median`: sign-independent balance between positive and negative pressure excursions around candidate strokes.
- `pulse_peak_to_peak_median`.

Bird-wing acoustic work shows that wing motion creates pressure impulses whose phase pattern varies with recording angle, so polarity itself is not treated as a decision rule. Biphasic morphology is retained only as a research measurement. Kurtosis and crest factor are standard measures of acoustic impulsiveness.

## Added spectral/time-frequency measurements

Calculated from loud frames between 150 Hz and 10 kHz:

- `spectral_centroid_hz`.
- `spectral_bandwidth_hz`.
- `spectral_rolloff85_hz`.
- `spectral_entropy`.
- `spectral_crest`.
- `spectral_flux_mean`, `spectral_flux_cv`.
- `spectral_comb_score`, `spectral_comb_spacing_hz`: diagnostic of regularly spaced spectral peaks/harmonic structure.

The harmonic-comb measurements are especially relevant to insect negatives, because insect flight tones are strongly characterized by a wingbeat fundamental and harmonics.

## Dataset/provenance fields

Xeno-canto rows preserve the XC number, species name, scientific-name components, recording type, quality, recordist, original filename, stated duration, remarks, and XC URL. FSD50K hard-negative rows preserve its labels, split, and the prior WING detection information.

These provenance fields should be included in train/test grouping so that a future classifier cannot obtain optimistic performance by learning recorder, uploader, codec, or dataset-specific artifacts instead of wing acoustics.
