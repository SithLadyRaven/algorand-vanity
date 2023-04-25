# Algorand Vanity
[![GitHub license](https://img.shields.io/github/license/sithladyraven/algorand-vanity.svg?style=social)](https://github.com/sithladyraven/algorand-vanity/blob/master/LICENSE) [![PyPI version](https://badge.fury.io/py/algorand-vanity.svg)](https://badge.fury.io/py/algorand-vanity) 

Python utility for generating vanity algorand wallet addresses.

## Installing from source
```bash
poetry install
```

## Installing with pip
```bash
pip install algorand-vanity
```

## Usage
```bash
algorand_vanity ADDRESS1 ADDRESS2
```

## Options
Option | Description | Default
--- | --- | ---
--threads, -t {start, end} | Number of threads to use for address generation | # of CPU cores
--filename, -f {start, end} | Filename to output addresses to | vanity_addresses
--location, -l {start, end} | location in address where the vanity string should be found | if not specified then string can be anywhere in the address
vanity | list of vanity addresses to search for **(Must only contain the following characters: A-Z, 2-7)** | required

