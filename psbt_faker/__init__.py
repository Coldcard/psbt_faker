#!/usr/bin/env python3
#
# To use this, install with:
#
#   pip install --editable .
#
# That will create the command "psbt_faker" in your path... or just use "./main.py ..." here
#
#
import click, io, pyqrcode, os
from binascii import b2a_hex as _b2a_hex
from base64 import b64encode
from decimal import Decimal
from .txn import fake_ms_txn, fake_txn, ADDR_STYLES
from .multisig import from_simple_text
from bbqr import split_qrs
from PIL import Image, ImageDraw, ImageChops


b2a_hex = lambda a: str(_b2a_hex(a), 'ascii')
#xfp2hex = lambda a: b2a_hex(a[::-1]).upper()

SIM_XPUB = 'tpubD6NzVbkrYhZ4XzL5Dhayo67Gorv1YMS7j8pRUvVMd5odC2LBPLAygka9p7748JtSq82FNGPppFEz5xxZUdasBRCqJqXvUHq6xpnsMcYJzeh'

def parse_int_string(v):
    return int(v, 0)

def repeat_until_length(values, target_length):
    # Creates a list of target_length length, by repeating the values.
    return [values[i % len(values)] for i in range(target_length)]

@click.command()
@click.argument('out_psbt', type=click.File('wb'), metavar="OUTPUT.PSBT")
@click.argument('xpub', type=str, default=SIM_XPUB)
@click.option('--num-ins', '-i', help="Number of inputs (default 1)", default=1)
@click.option('--sequence', '-S', help="Sequence number for each input", multiple=True, type=parse_int_string)
@click.option('--num-outs', '-o', help="Number of all txn outputs (default 2)", default=2)
@click.option('--output-amount', '-O', help="Amount of each non-change output in sats (default: all outputs are the same)", multiple=True, default=(), type=int)
@click.option('--num-change', '-c', help="Number of change outputs (default 1) from num-outs", default=1)
@click.option('--fee', '-f', help="Miner's fee in Satoshis", default=1000)
@click.option('--psbt2', '-2', help="Make PSBTv2", is_flag=True, default=False)
@click.option('--bbqr', '-b', help="Output BBQr OUTPUT.gif in CWD", is_flag=True, default=False)
@click.option('--segwit', '-s', help="[SS] Make inputs be segwit style", is_flag=True, default=False)
@click.option('--wrapped', '-w', help="[SS] Make inputs be wrapped segwit style (requires --segwit flag)", is_flag=True, default=False)
@click.option('--styles', '-a',  help="Output address style (multiple ok). If multisig only applies to non-change addresses.", multiple=True, default=None, type=click.Choice(ADDR_STYLES))
@click.option('--base64', '-6', help="Output base64 (default binary)", is_flag=True, default=False)
@click.option('--testnet', '-t', help="Assume testnet4 addresses (default mainnet)", is_flag=True, default=False)
@click.option('--partial', '-p', help="[SS] Change first input so its different XPUB and result cannot be finalized", is_flag=True, default=False)
@click.option('--zero-xfp', '-z', help="[SS] Provide zero XFP and junk XPUB (cannot be signed, but should be decodable)", is_flag=True, default=False)
@click.option('--multisig', '-m', type=click.File('rt'), metavar="config.txt", help="[MS] CC Multisig config file (text)", default=None)
@click.option('--locktime', '-l', help="nLocktime value (default 0), use 'current' to fetch best block height from mempool.space", default="0")
@click.option('--input-amount', '-n', help="Size of each input in sats (default 100k sats each input)", default=(100000,), multiple=True, type=int)
@click.option('--incl-xpubs', '-I',  help="[MS] Include XPUBs in PSBT global section", is_flag=True, default=False)
def main(num_ins, sequence, num_change, num_outs, output_amount, out_psbt, testnet, xpub, segwit, fee, styles, base64,
         partial, zero_xfp, multisig, locktime, input_amount, psbt2, incl_xpubs, wrapped, bbqr):
    '''Construct a valid PSBT which spends non-existant BTC to random addresses!'''

    if locktime == "current":
        try:
            import urllib.request
            u = urllib.request.urlopen("https://mempool.space/api/blocks/tip/height")
            locktime = int(u.read().decode())
        except:
            locktime = 0
    else:
        locktime = int(locktime)

    input_amount = repeat_until_length(input_amount, num_ins)
    change_outputs=list(range(num_change)) # always the first outputs

    outvals = None
    if output_amount: # not empty
        output_amount = repeat_until_length(output_amount, num_outs - num_change)
        if num_change > 0:
            change_amount = int(round((sum(input_amount) - fee - sum(output_amount)) / num_change))
            if change_amount <= 0:
                raise ValueError("Change amount is too large")
            outvals = [change_amount] * num_change + output_amount
        else:
            outvals = output_amount
        # Update to final fee, after rounding and change amount calculation.
        fee = sum(input_amount) - sum(outvals)

    if len(sequence) > 0:
        sequence = repeat_until_length(sequence, num_ins)
    else:
        sequence = None

    if multisig:
        ms_config = multisig.read()
        name, af, keys, M, N = from_simple_text(ms_config.split("\n"))
        psbt, outs = fake_ms_txn(input_amount, num_outs, M, keys, fee=fee, outvals=outvals, locktime=locktime,
                                 change_outputs=change_outputs, outstyles=styles,
                                 psbt_v2=psbt2, change_af=af,
                                 incl_xpubs=incl_xpubs, sequences=sequence, is_testnet=testnet)
    else:
        if zero_xfp:
            xpub = None

        psbt, outs = fake_txn(input_amount, num_outs, master_xpub=xpub, outvals=outvals, fee=fee,
                              segwit_in=segwit, outstyles=styles, locktime=locktime,
                              partial=partial, is_testnet=testnet, wrapped=wrapped,
                              change_outputs=change_outputs,
                              psbt_v2=psbt2, sequences=sequence)

    res = b64encode(psbt) if base64 else psbt
    out_psbt.write(res)

    print(f"\nFake PSBT would send {(sum(input_amount)/Decimal(1E8))} BTC to: ")
    print('\n'.join(" %.8f => %s %s" % (Decimal(amt)/Decimal(1E8),dest, ' (change back)' if chg else '')
                                                                for amt,dest,chg in outs))
    if fee:
        print(" %.8f => miners fee" % (Decimal(fee)/Decimal(1E8)))

    print("\nPSBT to be signed: " + out_psbt.name, end='\n\n')

    if bbqr:
        bbqr_out_file = os.path.splitext(out_psbt.name)[0] + ".gif"
        vers, parts = split_qrs(res, type_code="U" if base64 else "P", encoding="2",
                                max_version=20)
        qs = [pyqrcode.create(data, error='L', version=vers, mode='alphanumeric') for
              data in parts]

        frames = []
        num_parts = len(parts)
        for i in range(num_parts):
            xbm = qs[i].xbm(scale=4, quiet_zone=10)
            img = ImageChops.invert(Image.open(io.BytesIO(xbm.encode()))).convert('L')
            if num_parts > 1:
                # add progress bar
                pw = img.width // num_parts
                lm = (img.width - (pw * num_parts)) // 2
                draw = ImageDraw.Draw(img)
                h = 4 // 2
                y = img.height - h - (4 // 2) - 1

                for j in range(num_parts):
                    draw.rectangle((lm + (j * pw), y, lm + ((j + 1) * pw), y + h), fill=(128 if i != j else 0))

            frames.append(img)

        if num_parts == 1:
            frames[0].save(bbqr_out_file)
        else:
            frames[0].save(bbqr_out_file, format="gif", save_all=True, loop=0,
                           duration=250, default_image=False, append_images=frames[1:])


if __name__ == '__main__':
    main()

# EOF
