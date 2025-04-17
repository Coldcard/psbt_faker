import re
from .bip32 import BIP32Node

def from_simple_text(lines):
    # standard multisig file format - more than one line
    M, N = -1, -1
    deriv = None
    name = None
    xpubs = []
    addr_fmt = "p2sh"
    for ln in lines:
        # remove comments
        comm = ln.find('#')
        if comm == 0:
            continue
        if comm != -1:
            if not ln[comm + 1:comm + 2].isdigit():
                ln = ln[0:comm]

        ln = ln.strip()

        if ':' not in ln:
            if 'pub' in ln:
                # pointless optimization: allow bare xpub if we can calc xfp
                label = '00000000'
                value = ln
            else:
                # complain?
                # if ln: print("no colon: " + ln)
                continue
        else:
            label, value = ln.split(':', 1)
            label = label.lower()

        value = value.strip()

        if label == 'name':
            name = value
        elif label == 'policy':
            try:
                # accepts: 2 of 3    2/3    2,3    2 3   etc
                mat = re.search(r'(\d+)\D*(\d+)', value)
                assert mat
                M = int(mat.group(1))
                N = int(mat.group(2))
                assert 1 <= M <= N <= 15
            except:
                raise AssertionError('bad policy line')

        elif label == 'derivation':
            # reveal the path derivation for following key(s)
            try:
                assert value, 'blank'
                deriv = value
            except BaseException as exc:
                raise AssertionError('bad derivation line: ' + str(exc))

        elif label == 'format':
            # pick segwit vs. classic vs. wrapped version
            value = value.lower()
            assert value in ['p2wsh', 'p2sh', 'p2sh-p2wsh', 'p2wsh-p2sh']
            addr_fmt = value

        elif len(label) == 8:
            xpubs.append((label, deriv, BIP32Node.from_hwif(value)))

    return name, addr_fmt, xpubs, M, N