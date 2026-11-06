"""Plot descriptive recording-level feature ECDFs; requires matplotlib/pandas/NumPy."""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis_dir', type=Path)
    args = parser.parse_args()
    data = pd.read_csv(args.analysis_dir / 'candidate_recording_summaries.csv')
    features = [
        ('band1_150_600_modulation', '150–600 Hz envelope modulation'),
        ('selected_acc_noise_contrast', 'Selected accompaniment noise contrast'),
        ('spectral_flux_cv', 'Normalized spectral flux CV'),
        ('ipi_cv', 'Inter-pulse interval CV'),
        ('pulse_fwhm_ms_median', 'Envelope half-height width (ms)'),
        ('band_sync_lag_spread_ms', 'Band synchrony lag spread (ms)'),
        ('pulse_amp_cv', 'Pulse amplitude CV'),
        ('spectral_flux_mean', 'Mean normalized spectral flux'),
        ('wing_periodicity', 'Production broadband periodicity'),
    ]
    colors = {'xc_positive': '#237c8b', 'fsd_hard_negative': '#bb5a33'}
    labels = {'xc_positive': 'XC wingbeat-containing recordings (weak labels)',
              'fsd_hard_negative': 'FSD non-Animal hard negatives'}
    fig, axes = plt.subplots(3, 3, figsize=(13, 10))
    for ax, (feature, label) in zip(axes.flat, features):
        for source, group in data.groupby('source', sort=False):
            values = np.sort(group[feature].dropna().to_numpy())
            ax.step(values, np.arange(1, len(values)+1)/len(values), where='post',
                    color=colors[source], label=labels[source], linewidth=1.8)
        values = data[feature].dropna().to_numpy()
        lower, upper = np.quantile(values, [.01, .99])
        if lower < upper:
            ax.set_xlim(lower, upper)
        ax.set_ylim(0, 1)
        ax.set_xlabel(label, fontsize=10)
        ax.set_ylabel('Fraction of recordings', fontsize=9)
        ax.grid(alpha=.18)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Current-WING candidate populations: feature distributions', fontsize=17, y=.995)
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc='upper center', bbox_to_anchor=(.5, .97), ncol=2, frameon=False, fontsize=10)
    fig.text(.5, .014, 'One median per recording over accepted windows. Horizontal axes show pooled 1st–99th percentiles.\n'
             'Source populations are confounded; these are descriptive distributions, not detector sensitivity or validated class separation.',
             ha='center', fontsize=9, color='#444444')
    fig.tight_layout(rect=(0, .055, 1, .925))
    fig.savefig(args.analysis_dir / 'feature_distributions.png', dpi=180, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
