# PSBT Faker

A simple program to create test PSBT files, that are plausible and
self-consistent so that PSBT-signing tools will actually sign them.
Does not involve any blockchains... completely made up inputs and 
output addresses are chosen at random.

You should use the XPUB of the Coldcard you want experiment against.
This can be retrieved using `ckcc xpub` with the `ckcc-protocol`
CLI tool, or by exporting the wallet (see Advanced > MicroSD > Export Wallet menu).

For the Coldcard Simulator, you could use `tpubD6NzVbkrYhZ4XzL5Dhayo67Gorv1YMS7j8pRUvVMd5odC2LBPLAygka9p7748JtSq82FNGPppFEz5xxZUdasBRCqJqXvUHq6xpnsMcYJzeh` which is also default.

## Installation

```sh
git clone https://github.com/Coldcard/psbt_faker.git
cd psbt_faker
python3 -m pip install -U pip setuptools
python3 -m pip install --editable .
rehash
```

## Usage

```sh
$ psbt_faker --help
Usage: psbt_faker [OPTIONS] OUTPUT.PSBT [XPUB]

  Construct a valid PSBT which spends non-existant BTC to random addresses!

Options:
  -i, --num-ins INTEGER           Number of inputs (default 1)
  -o, --num-outs INTEGER          Number of all txn outputs (default 2)
  -c, --num-change INTEGER        Number of change outputs (default 1) from
                                  num-outs
  -f, --fee INTEGER               Miner's fee in Satoshis
  -2, --psbt2                     Make PSBTv2
  -s, --segwit                    [SS] Make inputs be segwit style
  -w, --wrapped                   [SS] Make inputs be wrapped segwit style
                                  (requires --segwit flag)
  -a, --styles [p2wsh|p2sh|p2sh-p2wsh|p2wsh-p2sh|p2wpkh|p2pkh|p2wpkh-p2sh|p2sh-p2wpkh|p2tr]
                                  Output address style (multiple ok). If
                                  multisig only applies to non-change
                                  addresses.
  -6, --base64                    Output base64 (default binary)
  -t, --testnet                   Assume testnet4 addresses (default mainnet)
  -p, --partial                   [SS] Change first input so its different
                                  XPUB and result cannot be finalized
  -z, --zero-xfp                  [SS] Provide zero XFP and junk XPUB (cannot
                                  be signed, but should be decodable)
  -m, --multisig config.txt       [MS] CC Multisig config file (text)
  -l, --locktime TEXT             nLocktime value (default 0), use 'current'
                                  to fetch best block height from
                                  mempool.space
  -n, --input-amount INTEGER      Size of each input in sats (default 100k
                                  sats each input)
  -I, --incl-xpubs                [MS] Include XPUBs in PSBT global section
  --help                          Show this message and exit.
```

Options with `[MS]` are not supported & ignored for single-sig.
Options with `[SS]` are not supported & ignored for multi-sig.

## Examples

```sh
$ export XPUB=tpubD6NzVbkrYhZ4Xp6tGusznF6KMdYHy1JSCdDk3XVLDuAA7EgJKghA5J1FP4pDXb4sCypJjAYPB4uTTXkVo2iWzK8BsMaccXTNyShDx3gxagi

$ psbt_faker foo.psbt $XPUB -s -a p2wsh --fee 15000000 -n 300000000 -o 1 -c 0

Fake PSBT would send 3 BTC to: 
 2.85000000 => bc1qppvspp5ahvjg28rv90644857c5df3mwr7ypcy7a093n90prg992qtjkkgv 
 0.15000000 => miners fee


$ psbt_faker foo.psbt $XPUB -o 10 -n 300000000

Fake PSBT would send 3 BTC to: 
 0.29999900 => 12YjQWLgh1TAtSzSS1BHKQaCrhEd2Cypv4  (change back)
 0.29999900 => 136QZHT1icbGUkQNcAv4CLFp6Gfoxf9ixN 
 0.29999900 => 1M667r3frAjiLMWucHS14MBcgtmAjYL6fi 
 0.29999900 => 17puZckh3RzNaac3XmX2JYFaF4wNrNu1ng 
 0.29999900 => 1HbtSJcovvkTpCuKq7UPVfYyTg7G8wAdAk 
 0.29999900 => 1CYN8P1vPyfCscsUbWy2nRU4tLccewtBVQ 
 0.29999900 => 1KhMtnJGSk9pRN2DrGgEzdEZUs8w1H4zna 
 0.29999900 => 1Dx6uFvs2jY4xA4o9g36UFwSqrSGsUzxhD 
 0.29999900 => 1CvBjipyE9Vbdi8AJw345YMbhvq7TbTN7u 
 0.29999900 => 1AW1Z4oseyWj6ib2CkwYY9eEBS5mkvgymN 
 0.00001000 => miners fee


$ psbt_faker foo.psbt $XPUB -n 10000000000  -o 13 -c 10

Fake PSBT would send 100 BTC to: 
 7.69230692 => 12YjQWLgh1TAtSzSS1BHKQaCrhEd2Cypv4  (change back)
 7.69230692 => 1Pqtjz6c6fg3pduEGmnzUbBbZ8JzgERtR5  (change back)
 7.69230692 => 1DsDJeZwmwsU9TY2vEmsVMWMfDrtGHHc2T  (change back)
 7.69230692 => 18W8nXPVKwUFovKpTffLbL3uik3x4Qf6TX  (change back)
 7.69230692 => 1qNozdz8fFMn7LVszM77WYwoJowUtKyaY  (change back)
 7.69230692 => 1AtvwyUV634pGG46wyuZkZ5WhK7UCrhdgf  (change back)
 7.69230692 => 1ABABZuHK2VF5w8pHQE23878adHYXSPWz3  (change back)
 7.69230692 => 1GSfhvFLj75Xz7cHsLMMaLhuLMoYaUna4B  (change back)
 7.69230692 => 16fBJHM7z91JxSnbrcHsDYTviespdouXUT  (change back)
 7.69230692 => 1errmuAqcQNMW42XG1p2G7RqX2uBqeF8F  (change back)
 7.69230692 => 15Kd3GBpTqbS6rzMMKHDPnSAktUoKDRqgc 
 7.69230692 => 15wErNoy7QSgovSHWUPWUt73fAs3bq98gN 
 7.69230692 => 1NkpHeWJ1dXeYQP8CWp6NuVLkTsZpNKQjx 
 0.00001000 => miners fee


psbt_faker foo.psbt $XPUB -o 10 -a p2wpkh -a p2wsh -a p2sh -a p2pkh -a p2wsh-p2sh -a p2wpkh-p2sh

Fake PSBT would send 0.001 BTC to: 
 0.00009900 => bc1qzruxkvnknt2xmqu9y5pr09n4ewhtm89w6mfelv  (change back)
 0.00009900 => bc1qc6yc0dmeu7tshepwsa7q8gwmxsa64gv0u476kqgdlruvndqe7nmsqh6krs 
 0.00009900 => 37UA1NpD2XNyLcn1eQXAFjJn3SFssXS84V 
 0.00009900 => 1A3okvZp3wGF2XZNqRhd8AAR23KH7rxt8W 
 0.00009900 => 34U4wbXXDsgn7Msr3Z1dgRybqLgJ2uN3qL 
 0.00009900 => 35FWGXE75wiedtsUe873qmKNZqJyCruCEf 
 0.00009900 => bc1q8qwl4vyj2avfa95st5zc5yj28kq4t874f0qkfk 
 0.00009900 => bc1qsxjshmg4zn6mul23gq2wk868qpm3f3tcmaqvr7zkz2xf6vwvl3vsqszsl6 
 0.00009900 => 3G4GWg8v9mCQA9rFVncgyYPZqRSuQmhs7o 
 0.00009900 => 1Fwnq5tgepfYytk4n6cHcAjA44fXB7AYMz 
 0.00001000 => miners fee
 

# how much BTC is send is regulated by -n/--input-amount and -i/--num-ins
# by default all inputs have size of 100k SATS
# below: 3 inputs each sending 1 million SATS
psbt_faker foo.psbt $XPUB -i 3 -n 1000000

Fake PSBT would send 0.03 BTC to: 
 0.01499500 => 12YjQWLgh1TAtSzSS1BHKQaCrhEd2Cypv4  (change back)
 0.01499500 => 1Cadzk6VAJaQasRnAxgoC43DUoDcq6dGua 
 0.00001000 => miners fee
 

# fetches actual block height from mempool.space
psbt_faker foo.psbt $XPUB -i 3 -n 10000000 -s -w --locktime current

Fake PSBT would send 0.3 BTC to: 
 0.14999500 => 3GcLByjaiNtTriQx2pSiU1sJoENFfKiUaf  (change back)
 0.14999500 => 32VSUWdkJDGEJSuKd1oRUoowy22ThyA7LB 
 0.00001000 => miners fee

PSBT to be signed: foo.psbt

 
psbt_faker foo.psbt -o 10 -a p2wpkh -a p2wsh -a p2sh -a p2pkh -a p2wsh-p2sh -a p2wpkh-p2sh --multisig ms-example-segwit.txt -c 3

Fake PSBT would send 0.001 BTC to: 
 0.00009900 => bc1qme4du64p8q3l8aedn83vdh4exe7a8mxelsdcwvcx67hgyd9jfqeshx863n  (change back)
 0.00009900 => bc1qc6qdln78rw8xhfc847v8jk4qdzx2pepvux3wrx403jmzwumqvwfq5st3vk  (change back)
 0.00009900 => bc1qngfqnl7p6pkrmpyz7ttcqt6mx3phq4c7dm23f2dvgvczmkfajjzq98cjpm  (change back)
 0.00009900 => bc1qpgdcenn3yecd0p28gk3guh4f2w4l4xrfas83z3 
 0.00009900 => bc1q6tvdfcn0emctdg3vvpx2kn40msan34glku9pm7tsn8557kzjyqzstuekem 
 0.00009900 => 3CC1pUNnrMqp7gG2GfPDZe4JmjrJEqpmnk 
 0.00009900 => 1AjT1kjfcbS8aMRQc27FwzknqeqzHzM7Vs 
 0.00009900 => 36w5DNqWSR3vuKNrZsLF42SnFfjkEMMHv2 
 0.00009900 => 3ETZ6Cp9Fsdrh5pkB9q9ay17E5JELJvma4 
 0.00009900 => bc1qwse4nh9ful5ww95j7ej8jw562tas6j8aqa6qd6 
 0.00001000 => miners fee
 
 
psbt_faker foo.psbt -i 3 -o 5 -c 3 -n 1000000000 --multisig ms-example-segwit.txt --incl-xpubs

Fake PSBT would send 30 BTC to: 
 5.99999800 => bc1qngfqnl7p6pkrmpyz7ttcqt6mx3phq4c7dm23f2dvgvczmkfajjzq98cjpm  (change back)
 5.99999800 => bc1qlt8yharuphh08l5trw96kz8w4jts2t45zwvafq72ma2rqgfktdvqcfa5xq  (change back)
 5.99999800 => bc1qnytf7s8crz35lwk6822kqdajdlr30n2tl43jusdx0q2q26gfneyssc3lc5  (change back)
 5.99999800 => bc1qrtz4gvmk453zplt78c264hkl3333f8xxcg2nq8cgvkrnucwgxzjqm05kge 
 5.99999800 => bc1qep2a66uh3kz20qk4vgr6yw8rezyzppszd3fyqzmmmt8xqamg66zqvjkg2h 
 0.00001000 => miners fee
 

# PSBT version 2
psbt_faker foo.psbt -i 3 -o 5 -c 3 -n 1000000000 --multisig ms-example-segwit.txt --psbt2 -a p2pkh

Fake PSBT would send 30 BTC to: 
 5.99999800 => bc1qngfqnl7p6pkrmpyz7ttcqt6mx3phq4c7dm23f2dvgvczmkfajjzq98cjpm  (change back)
 5.99999800 => bc1qlt8yharuphh08l5trw96kz8w4jts2t45zwvafq72ma2rqgfktdvqcfa5xq  (change back)
 5.99999800 => bc1qnytf7s8crz35lwk6822kqdajdlr30n2tl43jusdx0q2q26gfneyssc3lc5  (change back)
 5.99999800 => 1HRPDRJ9tVSpE2gsn2qfphJbXGneDsqiDA 
 5.99999800 => 1CW14Y5ZzjHSxCidm2wWBRwgeHmzsFNbQM 
 0.00001000 => miners fee
 
 
psbt_faker foo.psbt $XPUB -i 3  -n 100000000 --multisig ms-example.txt

Fake PSBT would send 3 BTC to: 
 1.49999500 => 3JeauQqiGXd5znAMums9KSpsXe8UhpS1tf  (change back)
 1.49999500 => 3Q7NmnYDxh4yyFuT152SQbLtFsn19EJVED 
 0.00001000 => miners fee


psbt_faker foo.psbt $XPUB -i 3  -o 10 -n 100000000 --multisig ms-example.txt --locktime 899000

Fake PSBT would send 3 BTC to: 
 0.29999900 => 3JeauQqiGXd5znAMums9KSpsXe8UhpS1tf  (change back)
 0.29999900 => 3NVNTQVFNwLEN5qBK7292cbSeQhY8DCDCm 
 0.29999900 => 3K4UA17iU9UXhULNa3yC5B3WB8qq6XE5hp 
 0.29999900 => 37kfug24cD6AhZhukJrDPRU5sxwAvAYwU6 
 0.29999900 => 38imUgvwSBJbo4CeUBQMFX7TeeKNsBnvdK 
 0.29999900 => 3CAzLxDv3fefoPQCDWkiuuwmsnSUBFzD4w 
 0.29999900 => 39SjZMdSfVAf5b2hBm1VmhegWYYHUnTnpn 
 0.29999900 => 38hJkV67aF6mX2Q6GGepGV8JModVs4k4VL 
 0.29999900 => 3L8uS7WF2K1Qbp3s8321zdZEpHJRo2KB2Z 
 0.29999900 => 3Euxvk1HcejZBc8VySTHp6icgieP4m2k7s 
 0.00001000 => miners fee
 
 
# extended private key can be used instead of extended public key XPUB for signle-sig PSBTs
# proper BIP-44 derivation path from master used in that case
XPRV=tprv8ZgxMBicQKsPeXJHL3vPPgTAEqQ5P2FD9qDeCQT4Cp1EMY5QkwMPWFxHdxHrxZhhcVRJ2m7BNWTz9Xre68y7mX5vCdMJ5qXMUfnrZ2si2X4

psbt_faker foo.psbt $XPRV -i 2  -o 2 -n 50000000 --locktime 899000 -s -w -6

Fake PSBT would send 1 BTC to: 
 0.49999500 => 36q7XpzinU7hM7eDaF37fBKV4sz73MPsfq  (change back)
 0.49999500 => 38q4ecMQt33o6HP1kh1dZJ6CdRcUUAdftd 
 0.00001000 => miners fee
 
 
# or use extended public key with key origin info to have "deeper" derivations in PSBT
# no validation is run against the xpub
XPUB='[0F056943/84h/1h/0h]tpubDC7jGaaSE66Pn4dgtbAAstde4bCyhSUs4r3P8WhMVvPByvcRrzrwqSvpF9Ghx83Z1LfVugGRrSBko5UEKELCz9HoMv5qKmGq3fqnnbS5E9r'

psbt_faker foo.psbt $XPUB -i 3  -o 3 -c 2 -n 50000000 --locktime current -s -6

Fake PSBT would send 1.5 BTC to: 
 0.49999666 => bc1qupyd58ndsh7lut0et0vtrq432jvu9jtdwgtkgk  (change back)
 0.49999666 => bc1qceytj4vfrg22cy7mp5mnfps4ffgseas20ak7fj  (change back)
 0.49999666 => bc1qj55nlp4ntq35sklzgq34pr0ujz2muuws5nrvrg 
 0.00001000 => miners fee
```
