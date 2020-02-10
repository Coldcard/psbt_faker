# PSBT Faker

A simple program to create test PSBT files, that are plausible and self-consistent so
the PSBT-signing tools will sign them. Does not involve any blockchains... completely
made up inputs.


## Usage

```
# python3 -m pip install --editable .
# rehash
# pbst_faker test.psbt 1destaddr
```

## Requirements

- `python3.6+`
- `pycoin` version 0.80
- `click`

(See `requirements.txt`)

