#!/usr/bin/env python3
#
# To use this, install with:
#
#   pip install --editable .
#
# That will create the command "psbt_faker" in your path... or just use "./main.py ..." here
#
#
import click
from binascii import b2a_hex as _b2a_hex
from base64 import b64encode
from .txn import *
from .ripemd import ripemd160
from .multisig import from_simple_text

b2a_hex = lambda a: str(_b2a_hex(a), 'ascii')
#xfp2hex = lambda a: b2a_hex(a[::-1]).upper()

SIM_XPUB = 'tpubD6NzVbkrYhZ4XzL5Dhayo67Gorv1YMS7j8pRUvVMd5odC2LBPLAygka9p7748JtSq82FNGPppFEz5xxZUdasBRCqJqXvUHq6xpnsMcYJzeh'


@click.command()
@click.argument('out_psbt', type=click.File('wb'), metavar="OUTPUT.PSBT")
@click.argument('xpub', type=str, default=SIM_XPUB)
@click.option('--num-outs', '-n', help="Number of outputs (default 1)", default=1)
@click.option('--num-change', '-c', help="Number of change outputs (default 1)", default=1)
@click.option('--value', '-v', help="Total BTC value of inputs (integer, default 3)", default=3)
@click.option('--fee', '-f', help="Miner's fee in Satoshis", default=1000)
@click.option('--segwit', '-s', help="Make ins/outs be segwit style", is_flag=True, default=False)
@click.option('--styles', '-a',  help="Output address style (multiple ok)", multiple=True, default=None, type=click.Choice(ADDR_STYLES))
@click.option('--base64', '-6', help="Output base64 (default binary)", is_flag=True, default=False)
@click.option('--testnet', '-t', help="Assume testnet3 addresses (default mainnet)", is_flag=True, default=False)
@click.option('--partial', '-p', help="Change first input so its different XPUB and result cannot be finalized", is_flag=True, default=False)
@click.option('--zero-xfp', '-z', help="Provide zero XFP and junk XPUB (cannot be signed, but should be decodable)", is_flag=True, default=False)
@click.option('--multisig', '-m', type=click.File('rt'), metavar="config.txt", help="[MS] CC Multisig config file (text)", default=None)
@click.option('--locktime', '-l', help="[MS] nLocktime value (default current block height)", default=None)
@click.option('--input-amount', '-n', help="[MS] Size of each input in sats (default 100k sats each input)", default=100000)
@click.option('--legacy', help="[MS] Make inputs be legacy p2sh style", is_flag=True, default=False)
def main(num_change, num_outs, out_psbt, value, testnet, xpub, segwit, fee, styles, base64, partial, zero_xfp, multisig, locktime, input_amount, legacy):
    '''Construct a valid PSBT which spends non-existant BTC to random addresses!'''

    num_ins = int(value)
    total_outs = num_outs + num_change

    # TODO: PSBTv2 if flag set

    if zero_xfp:
        xpub = None


    if multisig:
        # TODO: flag to include xpubs in header

        chg_style = 'p2sh' if not segwit else 'p2wsh'
        if not styles:
            styles = [chg_style]

        # TODO: slow getting this, better to estimate unless they want real value
        # TODO: for single-sig too
        # TODO: modulate value (today + 2 days, etc) for CCC testing/validation
        if locktime is None:        
            try:
                import urllib.request
                u = urllib.request.urlopen("https://mempool.space/api/blocks/tip/height")
                locktime = int(u.read().decode())
            except:
                locktime = 0

        ms_config = multisig.read()
        name, af, keys, M, N = from_simple_text(ms_config.split("\n"))
        psbt, outs = fake_ms_txn(num_ins, num_outs, M, keys, fee=fee, locktime=locktime,
                           change_outputs=list(range(num_change)), outstyles=styles,
                           segwit_in=not legacy, input_amount=input_amount)

    else:
        chg_style = 'p2pkh' if not segwit else 'p2wpkh'
        if not styles:
            styles = [chg_style]

        psbt, outs = fake_txn(num_ins, total_outs, master_xpub=xpub, fee=fee,
                        segwit_in=segwit, outstyles=styles, change_style=chg_style,
                        partial=partial,
                        is_testnet=testnet, change_outputs=list(range(num_outs, num_outs+num_change)))


    out_psbt.write(psbt if not base64 else b64encode(psbt))

    print(f"\nFake PSBT would send {num_ins} BTC to: ")
    print('\n'.join(" %.8f => %s %s" % (amt,dest, ' (change back)' if chg else '') 
                                                                for amt,dest,chg in outs))
    if fee:
        print(" %.8f => miners fee" % (Decimal(fee)/Decimal(1E8)))

    #print("\nPSBT to be signed: " + out_psbt.name, end='\n\n')


'''
@main.command('ms')
@click.argument('out_psbt', type=click.File('wb'), metavar="OUTPUT.PSBT")
@click.option('--num-ins', help="Number of inputs (default 1)", default=1)
@click.option('--num-outs', help="Number of outputs (default 1)", default=1)
@click.option('--num-change', '-c', help="Number of change outputs (default 1)", default=1)
@click.option('--fee', '-f', help="Miner's fee in Satoshis", default=1000)
@click.option('--styles', '-a',  help="Output address style (multiple ok)", multiple=True, default=None, type=click.Choice(ADDR_STYLES))
@click.option('--base64', '-6', help="Output base64 (default binary)", is_flag=True, default=False)
def ms_faker(ms_conf, out_psbt, num_ins, num_change, num_outs, legacy, fee, styles, base64,
             locktime, input_amount):
  ''Construct a valid multisig PSBT which spends non-existant BTC to random addresses!'''


if __name__ == '__main__':
    main()

# EOF
