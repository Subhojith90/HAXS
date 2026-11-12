# HAXS publication assets

This directory contains the immutable figure-generation inputs and outputs for
the HAXS code/data release. It intentionally contains no manuscript source or
compiled manuscript PDF.

## Contents

- `make_figures.py`: deterministic analysis and figure builder;
- `source_data/raw/`: complete primary, frozen-confirmation, and small-system
  ED/DTWA tables used by the figures;
- `source_data/*.csv`: paper-facing gate, occupancy, local-window, and variance
  summaries;
- `source_data/primary_lock.yaml`: frozen primary configuration;
- `figures/`: final vector and raster figure outputs.

## Regenerate figures

From this directory:

```bash
MPLCONFIGDIR=/tmp/haxs-mpl python make_figures.py
```

The generated outputs must reproduce the stored figures. The code/data release
does not contain the unpublished manuscript or its circulation deliverables.
