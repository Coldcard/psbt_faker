# PSBT Faker

A simple program to create test PSBT files, that are plausible and
self-consistent so that PSBT-signing tools will actually sign them.
Does not involve any blockchains... completely made up inputs and 
output addresses are chosen at random.

You should use the XPUB of the Coldcard you want experiment against.
This can be retreived using `ckcc xpub` with the `ckcc-protocol`
CLI tool, or by exporting the wallet (see Advanced > MicroSD > Export Wallet menu).

For the Coldcard Simulator, you could use:

    tpubD6NzVbkrYhZ4XzL5Dhayo67Gorv1YMS7j8pRUvVMd5odC2LBPLAygka9p7748JtSq82FNGPppFEz5xxZUdasBRCqJqXvUHq6xpnsMcYJzeh

## Usage

```
# python3 -m pip install --editable .
# rehash
# pbst_faker --help

Usage: psbt_faker [OPTIONS] OUTPUT.PSBT XPUB

  Construct a valid PSBT which spends non-existant BTC to random addresses!

Options:
  -n, --num-outs INTEGER          Number of outputs (default 1)
  -c, --num-change INTEGER        Number of change outputs (default 1)
  -v, --value INTEGER             Total BTC value of inputs (integer, default
                                  3)
  -f, --fee INTEGER               Miner's fee in Satoshis
  -s, --segwit                    Make ins/outs be segwit style
  -a, --styles [p2wpkh|p2wsh|p2sh|p2pkh|p2wsh-p2sh|p2wpkh-p2sh]
                                  Output address style (multiple ok)
  -6, --base64                    Output base64 (default binary)
  -t, --testnet                   Assume testnet3 addresses (default mainnet)
  --help                          Show this message and exit.
```

## Examples

```
$ export XPUB=tpubD6NzVbkrYhZ4Xp6tGusznF6KMdYHy1JSCdDk3XVLDuAA7EgJKghA5J1FP4pDXb4sCypJjAYPB4uTTXkVo2iWzK8BsMaccXTNyShDx3gxagi

$ psbt_faker foo.psbt $XPUB -s -a p2wsh --fee 15000000 -c 0

Fake PSBT would send 3 BTC to: 
 2.85000000 => bc1qqalzjffzy9nwcd35t0phdyugdmmqpskldgcw3xd40qxh32z908msf5alem 
 0.15000000 => miners fee

$ psbt_faker foo.psbt $XPUB -n 10

Fake PSBT would send 3 BTC to: 
 0.27272636 => 17VardgvHiYjDEtpBRWpqQLgrvKDUiGGaW 
 0.27272636 => 1A1FDLRD1caNjbwpr4odqpcB2sGgZSgGqZ 
 0.27272636 => 1P3Zr4zQko2CDbDDiqrkMduSppNB3Pb1Aq 
 0.27272636 => 1LcDusCVB6KjjAcrk5NvscV4AQ3cRJTR8j 
 0.27272636 => 15oy1fAxnbYr6Vgz7eNwjBQfujdvssdRaG 
 0.27272636 => 1EkYuiLo9Tt3cYCJwMfDvX38MddTBMqPc1 
 0.27272636 => 185VxgHqCEYudH6XXwdDiQtqfEUXGMxSXJ 
 0.27272636 => 19dR12aRSj8nyUaJLM11ruExa7N6jdAmUJ 
 0.27272636 => 1Ppj73d7z6cQvKhzezmaBywbJRSUnrymPE 
 0.27272636 => 1CPCdAWTrVqgS8cHVTbDQwkCvASjTfcaTe 
 0.27272636 => 1F2WTuA3BRpYmM82gsLuAdyAiLPYoUYijP  (change back)
 0.00001000 => miners fee


$ psbt_faker foo.psbt $XPUB -n 3 -v 100 -c 10

Fake PSBT would send 100 BTC to: 
 7.69230692 => 13mRoGiQHzmPhaCgQZbjw42njWhV3ymqDw 
 7.69230692 => 1MMbuGuuaJ9GnRXh4ixa6xiKER3xzg52TJ 
 7.69230692 => 1NjnUBrWSSx8iK5TC3XJXqQ7grC23kpZX2 
 7.69230692 => 1Aq96VVsd2nocTqAYQ4PnD6XhotKqmrBNn  (change back)
 7.69230692 => 1Bj7KprFDJ1d1F1se3DKedASFYvjWNaZMT  (change back)
 7.69230692 => 1HVTgLgZF95tF4B1CJk4BEvkLmT3hYDrmA  (change back)
 7.69230692 => 17Uz3tHeG1Zf8W4hmst2kQtbH17tHe3UTN  (change back)
 7.69230692 => 1LyLjaPcXbo5TxJYMYyUT9HzCgkJnKef1j  (change back)
 7.69230692 => 19DasuH8grQGc4MrPPR5abYUZAKF9UbbwZ  (change back)
 7.69230692 => 1JpymwTGWfXpcurLnsFbLcPRnkkzvRiKsy  (change back)
 7.69230692 => 1PoFUSStjmogrv2eEtRjbpz8N5reETVVZn  (change back)
 7.69230692 => 1Q8yrQsHotMNkrsAyEynDAuqC8rDs7nG41  (change back)
 7.69230692 => 1AbiaE64hjUygVoqkedaLvneHht8bbvPgo  (change back)
 0.00001000 => miners fee

psbt_faker foo.psbt $XPUB -n 10 -a p2wpkh -a p2wsh -a p2sh -a p2pkh -a p2wsh-p2sh -a p2wpkh-p2sh

Fake PSBT would send 3 BTC to: 
 0.27272636 => bc1q2l0zgfksxacs8hdxwmq56ftpzagcyvq8z237qf 
 0.27272636 => bc1q4ru6vpngexl348we0fkydheat3azcvr96uc975tmvcy0z8kjaz6qz30498 
 0.27272636 => 37Axq8rmQGjEHVoCb877RiNfWnnMtFCZ6H 
 0.27272636 => 16JDSqRVvYdWV4KntQ5wjUK5es6CaiTyBc 
 0.27272636 => 3HXq92K1xvx6QMNmQTHPWPLNiEReez595d 
 0.27272636 => 3LyBpZ2aaTs1Qj1NFmGGttL8PyhEzB9iDW 
 0.27272636 => bc1qsplnzq8n500q4zg6a8m2nj4c8ygvlp8p8zuppc 
 0.27272636 => bc1qw9hery5rjcujuf3f09djlxepepx6luen7jq9t0hfsu44dv3t6x3s4k4aw5 
 0.27272636 => 3Ld1TUaWQouRRGGAc8PSzvqtgjfyxdM3Vr 
 0.27272636 => 1ABmPHMdqK4MqF9BkACv8PHHYL7McmbYAq 
 0.27272636 => 15mkVohf2A1g9nVo9tn2KtN2f4eBHQCche  (change back)
 0.00001000 => miners fee


```
