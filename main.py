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
from psbt import BasicPSBT, BasicPSBTInput, BasicPSBTOutput
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

b2a_hex = lambda a: str(_b2a_hex(a), 'ascii')
#xfp2hex = lambda a: b2a_hex(a[::-1]).upper()

TESTNET = False

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

def calc_pubkey(xpubs, path):
    # given a map of paths to xpubs, and a single path, calculate the pubkey
    assert path[0:2] == 'm/'

    hard_prefix = '/'.join(s for s in path.split('/') if s[-1] == "'")
    hard_depth = hard_prefix.count('/') + 1

    want = ('m/'+hard_prefix) if hard_prefix else 'm'
    assert want in xpubs, f"Need: {want} to build pubkey of {path}"

    node = BIP32Node.from_hwif(xpubs[want])
    parts = [s for s in path.split('/') if s != 'm'][hard_depth:]

    # node = node.subkey_for_path(path[2:])
    if not parts:
        assert want == path
    else:
        for sk in parts:
            node = node.subkey_for_path(sk)

    return node.sec()
    

@click.command()
@click.argument('out_psbt', type=click.File('wb'))
@click.argument('payout_addresses', type=str, nargs='*')
@click.option('--testnet', '-t', help="Assume testnet3 addresses", is_flag=True, default=False)
@click.option('--xpub', help="Provide XPUB value", default=None)
@click.option('--num-change', '-c', help="Number of change outputs", default=1)
@click.option('--xfp', '--fingerprint', help="Provide XFP value, otherwise discovered from xpub", default=None)
def faker(num_change, payout_addresses, out_psbt, testnet, xfp=None, xpub=None):

    global TESTNET
    TESTNET = testnet

    ''' Match lines like:
            m/0'/0'/0' => n3ieqYKgVR8oB2zsHVX1Pr7Zc31pP3C7ZJ
            m/0/2 => mh7finD8ctq159hbRzAeevSuFBJ1NQjoH2
        and also 
            m => tpubD6NzVbkrYhZ4XzL5Dhayo67Gorv1YMS7j8pRUvVMd5odC2LBPLAygka9p7748JtSq82FNGPppFEz5xxZUdasBRCqJqXvUHq6xpnsMcYJzeh
    '''

    psbt = BasicPSBT()

    for path, addr in addrs:
        print(f"addr: {addr} ... ", end='')

        rr = explora('address', addr, 'utxo')

        if not rr:
            print('nada')
            continue

        here = 0
        for u in rr:
            here += u['value']

            tt = TxIn(h2b_rev(u['txid']), u['vout'])
            spending.append(tt)
            #print(rr)

            pin = BasicPSBTInput(idx=len(psbt.inputs))
            psbt.inputs.append(pin)

            pubkey = calc_pubkey(xpubs, path)

            pin.bip32_paths[pubkey] = str2path(xfp, path)

            # fetch the UTXO for witness signging
            td = explora('tx', u['txid'], 'hex', is_json=False)
            outpt = Tx.from_hex(td.decode('ascii')).txs_out[u['vout']]

            with BytesIO() as b:
                outpt.stream(b)
                pin.witness_utxo = b.getvalue()


        print('%.8f BTC' % (here / 1E8))
        total += here

        if len(spending) > 15:
            print("Reached practical limit on # of inputs. "
                    "You'll need to repeat this process again later.")
            break

    assert total

    print("Found total: %.8f BTC" % (total / 1E8))

    print("Planning to send to: %s" % payout_address)

    dest_scr = standard_tx_out_script(payout_address)

    txn = Tx(2,spending,[TxOut(total, dest_scr)])

    fee = tx_fee.recommended_fee_for_tx(txn)

    # placeholder, single output that isn't change
    pout = BasicPSBTOutput(idx=0)
    psbt.outputs.append(pout)

    print("Guestimate fee: %.8f BTC" % (fee / 1E8))

    txn.txs_out[0].coin_value -= fee

    # write txn into PSBT
    with BytesIO() as b:
        txn.stream(b)
        psbt.txn = b.getvalue()

    out_psbt.write(psbt.as_bytes())

    print("PSBT to be signed:\n\n\t" + out_psbt.name, end='\n\n')
    

if __name__ == '__main__':
    recovery()

# EOF
