#!/usr/bin/env python3
#
# To use this, install with:
#
#   pip install --editable .
#
# That will create the command "psbt_faker" in your path... or just use "./main.py ..." here
#
#
import click, sys, os, pdb, struct, io, json, re, time
from pprint import pformat, pprint
from binascii import b2a_hex as _b2a_hex
from binascii import a2b_hex
from io import BytesIO
from collections import namedtuple
from base64 import b64encode, b64decode
from pycoin.tx.Tx import Tx
from pycoin.tx.TxOut import TxOut
from pycoin.tx.TxIn import TxIn
from pycoin.ui import standard_tx_out_script
from pycoin.encoding import b2a_hashed_base58, hash160
from pycoin.serialize import b2h_rev, b2h, h2b, h2b_rev
from pycoin.contrib.segwit_addr import encode as bech32_encode
from pycoin.key.BIP32Node import BIP32Node
from pycoin.convention import tx_fee
import urllib.request

from .txn import *

b2a_hex = lambda a: str(_b2a_hex(a), 'ascii')
#xfp2hex = lambda a: b2a_hex(a[::-1]).upper()

def str2ipath(s):
    # convert text to numeric path for BIP174
    for i in s.split('/'):
        if i == 'm': continue
        if not i: continue      # trailing or duplicated slashes

        if i[-1] in "'ph":
            assert len(i) >= 2, i
            here = int(i[:-1]) | 0x80000000
        else:
            here = int(i)
            assert 0 <= here < 0x80000000, here

        yield here

def xfp2str(xfp):
    # Standardized way to show an xpub's fingerprint... it's a 4-byte string
    # and not really an integer. Used to show as '0x%08x' but that's wrong endian.
    return b2a_hex(struct.pack('>I', xfp)).upper()

def str2path(xfp, s):
    # output binary needed for BIP-174
    p = list(str2ipath(s))
    return struct.pack('<%dI' % (1 + len(p)), xfp, *p)

@click.command()
@click.argument('out_psbt', type=click.File('wb'), metavar="OUTPUT.PSBT")
@click.argument('xpub', type=str)
@click.option('--num-outs', '-n', help="Number of outputs (default 1)", default=1)
@click.option('--num-change', '-c', help="Number of change outputs (default 1)", default=1)
@click.option('--value', '-v', help="Total BTC value of inputs (integer, default 3)", default=3)
@click.option('--fee', '-f', help="Miner's fee in Satoshis", default=1000)
@click.option('--segwit', '-s', help="Make ins/outs be segwit style", is_flag=True, default=False)
@click.option('--styles', '-a',  help="Output address style (multiple ok)", multiple=True, default=None, type=click.Choice(ADDR_STYLES))
@click.option('--base64', '-6', help="Output base64 (default binary)", is_flag=True, default=False)
@click.option('--testnet', '-t', help="Assume testnet3 addresses (default mainnet)", is_flag=True, default=False)
def faker(num_change, num_outs, out_psbt, value, testnet, xpub, segwit, fee, styles, base64):
    '''Construct a valid PSBT which spends non-existant BTC to random addresses!'''

    num_ins = int(value)
    total_outs = num_outs + num_change

    chg_style = 'p2pkh' if not segwit else 'p2wpkh'

    if not styles:
        styles = [chg_style]

    psbt, outs = fake_txn(num_ins, total_outs, master_xpub=xpub, fee=fee,
                    segwit_in=segwit, outstyles=styles, change_style=chg_style,
                    is_testnet=testnet, change_outputs=list(range(num_outs, num_outs+num_change)))


    out_psbt.write(psbt if not base64 else b64encode(psbt))

    print(f"\nFake PSBT would send {num_ins} BTC to: ")
    print('\n'.join(" %.8f => %s %s" % (amt,dest, ' (change back)' if chg else '') for amt,dest,chg in outs))
    if fee:
        print(" %.8f => miners fee" % (Decimal(fee)/Decimal(1E8)))

    #print("\nPSBT to be signed: " + out_psbt.name, end='\n\n')

if __name__ == '__main__':
    faker()

# EOF
