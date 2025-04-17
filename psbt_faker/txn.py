#
# Creating fake transactions. Not simple... but only for testing purposes, so ....
#
import struct, random, hashlib
from .segwit_addr import encode as bech32_encode
from io import BytesIO
from decimal import Decimal
from .psbt import BasicPSBT, BasicPSBTInput, BasicPSBTOutput
from .base58 import encode_base58_checksum
from .ripemd import hash160
from .helpers import str2path
from .serialize import uint256_from_str
from .bip32 import BIP32Node
from .ctransaction import CTransaction, CTxIn, CTxOut, COutPoint

# all possible addr types, including multisig/scripts
ADDR_STYLES = ['p2wpkh', 'p2wsh', 'p2sh', 'p2pkh', 'p2wsh-p2sh', 'p2wpkh-p2sh', 'p2tr']

# single-signer
ADDR_STYLES_SINGLE = ['p2wpkh', 'p2pkh', 'p2wpkh-p2sh']
# multi-signer
ADDR_STYLES_MULTI = ['p2wsh', 'p2sh', 'p2sh-p2wsh', 'p2wsh-p2sh']

def prandom(count):
    # make some bytes, randomly, but not: deterministic
    return bytes(random.randint(0, 255) for i in range(count))

def fake_dest_addr(style='p2pkh'):
    # Make a plausible output address, but it's random garbage. Cant use for change outs

    # See CTxOut.get_address() in ../shared/serializations

    if style == 'p2wpkh':
        return bytes([0, 20]) + prandom(20)

    if style == 'p2wsh':
        return bytes([0, 32]) + prandom(32)

    if style == 'p2tr':
        return bytes([1, 32]) + prandom(32)

    if style in ['p2sh', 'p2wsh-p2sh', 'p2wpkh-p2sh']:
        # all equally bogus P2SH outputs
        return bytes([0xa9, 0x14]) + prandom(20) + bytes([0x87])

    if style == 'p2pkh':
        return bytes([0x76, 0xa9, 0x14]) + prandom(20) + bytes([0x88, 0xac])

    # missing: if style == 'p2pk' =>  pay to pubkey, considered obsolete

    raise ValueError('not supported: ' + style)

def make_change_addr(wallet, style):
    # provide script, pubkey and xpath for a legit-looking change output

    redeem_scr, actual_scr = None, None
    deriv = [12, 34, random.randint(0, 1000)]

    xfp, = struct.unpack('I', wallet.fingerprint())

    dest = wallet.subkey_for_path('/'.join(str(i) for i in deriv))

    target = dest.hash160()
    assert len(target) == 20

    is_segwit = False
    if style == 'p2pkh':
        redeem_scr = bytes([0x76, 0xa9, 0x14]) + target + bytes([0x88, 0xac])
    elif style == 'p2wpkh':
        redeem_scr = bytes([0, 20]) + target
        is_segwit = True
    elif style == 'p2wpkh-p2sh':
        redeem_scr = bytes([0, 20]) + target
        actual_scr = bytes([0xa9, 0x14]) + hash160(redeem_scr) + bytes([0x87])
    else:
        raise ValueError('cant make fake change output of type: ' + style)

    return redeem_scr, actual_scr, is_segwit, dest.sec(), struct.pack('4I', xfp, *deriv)

def fake_txn(num_ins, num_outs, master_xpub=None, subpath="0/%d", fee=10000,
             outvals=None, segwit_in=False, outstyles=['p2pkh'], is_testnet=False,
             change_style='p2pkh', partial=False,
             change_outputs=[]):

    # make various size txn's ... completely fake and pointless values
    # - but has UTXO's to match needs
    # - input total = num_inputs * 1BTC
    from struct import pack

    psbt = BasicPSBT()
    txn = CTransaction()
    txn.nVersion = 2

    # we have a key; use it to provide "plausible" value inputs
    if master_xpub:
        mk = BIP32Node.from_wallet_key(master_xpub)
        xfp = mk.fingerprint()
    else:
        # special value for COLDCARD: zero xfp => anyone can try to sign
        mk = BIP32Node.from_master_secret(b'1'*32)
        xfp = bytes(4)

    psbt.inputs = [BasicPSBTInput(idx=i) for i in range(num_ins)]
    psbt.outputs = [BasicPSBTOutput(idx=i) for i in range(num_outs)]

    outputs = []

    for i in range(num_ins):
        # make a fake txn to supply each of the inputs
        # - each input is 1BTC

        # addr where the fake money will be stored.
        subkey = mk.subkey_for_path(subpath % i)
        sec = subkey.sec()
        assert len(sec) == 33, "expect compressed"
        assert subpath[0:2] == '0/'

        if partial and (i == 0):
            psbt.inputs[i].bip32_paths[sec] = b'Nope' + pack('<II', 0, i)
        else:
            psbt.inputs[i].bip32_paths[sec] = xfp + pack('<II', 0, i)

        supply = CTransaction()
        supply.nVersion = 2
        out_point = COutPoint(
            uint256_from_str(struct.pack('4Q', 0xdead, 0xbeef, 0, 0)),
            73
        )
        supply.vin = [CTxIn(out_point, nSequence=0xffffffff)]

        if segwit_in:
            # p2wpkh
            scr = bytes([0x00, 0x14]) + subkey.hash160()
        else:
            # p2pkh
            scr = bytes([0x76, 0xa9, 0x14]) + subkey.hash160() + bytes([0x88, 0xac])

        supply.vout.append(CTxOut(int(1E8), scr))

        if segwit_in:
            # just utxo for segwit
            psbt.inputs[i].witness_utxo = supply.vout[-1].serialize()
        else:
            # whole tx for pre-segwit
            psbt.inputs[i].utxo = supply.serialize_with_witness()

        supply.calc_sha256()

        spendable = CTxIn(COutPoint(supply.sha256, 0), nSequence=0xffffffff)
        txn.vin.append(spendable)

    for i in range(num_outs):
        is_change = False

        # random P2PKH
        if not outstyles:
            style = ADDR_STYLES[i % len(ADDR_STYLES)]
        else:
            style = outstyles[i % len(outstyles)]

        if i in change_outputs:
            scr, act_scr, isw, pubkey, sp = make_change_addr(mk, change_style)
            psbt.outputs[i].bip32_paths[pubkey] = sp
            is_change = True
        else:
            scr = act_scr = fake_dest_addr(style)
            isw = ('w' in style)

        assert scr
        act_scr = act_scr or scr

        if isw:
            psbt.outputs[i].witness_script = scr
        elif style.endswith('sh'):
            psbt.outputs[i].redeem_script = scr

        if not outvals:
            h = CTxOut(int(round(((1E8*num_ins)-fee) / num_outs, 4)), act_scr)
        else:
            h = CTxOut(int(outvals[i]), act_scr)

        outputs.append((Decimal(h.nValue)/Decimal(1E8), act_scr, is_change) )

        txn.vout.append(h)


    psbt.txn = txn.serialize()

    rv = BytesIO()
    psbt.serialize(rv)

    return rv.getvalue(), [(n, render_address(s, is_testnet), ic) for n,s,ic in outputs]


def make_redeem(M, keys, idx, is_change, bip67=True):
    # Construct a redeem script, and ordered list of xfp+path to match.
    N = len(keys)

    # see BIP 67: <https://github.com/bitcoin/bips/blob/master/bip-0067.mediawiki>

    data = []
    for cosigner_idx, (xfp, str_path, node) in enumerate(keys):
        sp = f"{int(is_change)}/{idx}"
        n = node.subkey_for_path(sp)
        pk = n.sec()
        data.append((pk, str2path(xfp, str_path + "/" + sp)))

    if bip67:
        data.sort(key=lambda i: i[0])

    mm = [80 + M] if M <= 16 else [1, M]
    nn = [80 + N] if N <= 16 else [1, N]

    rv = bytes(mm)

    for pk, _ in data:
        rv += bytes([len(pk)]) + pk

    rv += bytes(nn + [0xAE])

    return rv, data

def make_ms_address(M, keys, idx, is_change, addr_fmt="p2wsh", testnet=1, bip67=True):
    # Construct addr and script need to represent a p2sh address
    script, bip32paths = make_redeem(M, keys, idx, is_change, bip67=bip67)

    if addr_fmt == "p2wsh":
        # testnet=2 --> regtest
        hrp = ['bc', 'tb', 'bcrt'][testnet]
        data = hashlib.sha256(script).digest()
        addr = bech32_encode(hrp, 0, data)
        scriptPubKey = bytes([0x0, 0x20]) + data
    else:
        if addr_fmt == "p2sh":
            digest = hash160(script)
        elif addr_fmt in ("p2sh-p2wsh", "p2wsh-p2sh"):
            digest = hash160(b'\x00\x20' + hashlib.sha256(script).digest())
        else:
            raise ValueError(addr_fmt)

        prefix = bytes([196]) if testnet else bytes([5])
        addr = encode_base58_checksum(prefix + digest)

        scriptPubKey = bytes([0xa9, 0x14]) + digest + bytes([0x87])

    return addr, scriptPubKey, script, bip32paths


def fake_ms_txn(num_ins, num_outs, M, keys, fee=10000, outvals=None, segwit_in=True,
                outstyles=['p2wsh'], change_outputs=[], incl_xpubs=False,
                input_amount=1E8, bip67=True, locktime=0, testnet=False):
    # make various size MULTISIG txn's ... completely fake and pointless values
    # - but has UTXO's to match needs
    psbt = BasicPSBT()
    # if psbt_v2 is None:
    #     # anything passed directly to this function overrides
    #     # pytest flag --psbt2 - only care about pytest flag
    #     # if psbt_v2 is not specified (None)
    #     psbt_v2 = pytestconfig.getoption('psbt2')
    #
    # if psbt_v2:
    #     psbt.version = 2
    #     psbt.txn_version = 2
    #     psbt.input_count = num_ins
    #     psbt.output_count = num_outs

    txn = CTransaction()
    txn.nVersion = 2
    txn.nLockTime = locktime

    if incl_xpubs:
        # add global header with XPUB's
        for idx, (xfp, str_path, node) in enumerate(keys):
            kk = str2path(xfp, str_path)
            psbt.xpubs.append((node.node.serialize_public(), kk))

    psbt.inputs = [BasicPSBTInput(idx=i) for i in range(num_ins)]
    psbt.outputs = [BasicPSBTOutput(idx=i) for i in range(num_outs)]

    for i in range(num_ins):
        # make a fake txn to supply each of the inputs
        # - each input is 1BTC

        # addr where the fake money will be stored.
        addr, scriptPubKey, script, details = make_ms_address(M, keys, i, True,
                                                              addr_fmt="p2wsh" if segwit_in else "p2sh",
                                                              bip67=bip67)

        # lots of supporting details needed for p2sh inputs
        if segwit_in:
            psbt.inputs[i].witness_script = script
        else:
            psbt.inputs[i].redeem_script = script

        for pubkey, xfp_path in details:
            psbt.inputs[i].bip32_paths[pubkey] = xfp_path

        # UTXO that provides the funding for to-be-signed txn
        supply = CTransaction()
        supply.nVersion = 2
        out_point = COutPoint(
            uint256_from_str(struct.pack('4Q', 0xdead, 0xbeef, 0, 0)),
            73
        )
        supply.vin = [CTxIn(out_point, nSequence=0xffffffff)]

        supply.vout.append(CTxOut(int(input_amount), scriptPubKey))

        if not segwit_in:
            psbt.inputs[i].utxo = supply.serialize_with_witness()
        else:
            psbt.inputs[i].witness_utxo = supply.vout[-1].serialize()

        supply.calc_sha256()
        # if psbt_v2:
        #     psbt.inputs[i].previous_txid = supply.hash
        #     psbt.inputs[i].prevout_idx = 0
        #     # TODO sequence
        #     # TODO height timelock
        #     # TODO time timelock

        seq = 0xffffffff
        if (i == 0) and locktime:
            # need to decrement at least one for locktime to work
            seq -= 1
        spendable = CTxIn(COutPoint(supply.sha256, 0), nSequence=seq)
        txn.vin.append(spendable)

    for i in range(num_outs):
        if not outstyles:
            style = ADDR_STYLES_MULTI[i % len(ADDR_STYLES_MULTI)]
        elif len(outstyles) == num_outs:
            style = outstyles[i]
        else:
            style = outstyles[i % len(outstyles)]

        if i in change_outputs:
            addr, scriptPubKey, scr, details = make_ms_address(M, keys, num_ins+i, False,
                                                               addr_fmt=style, bip67=bip67)

            for pubkey, xfp_path in details:
                psbt.outputs[i].bip32_paths[pubkey] = xfp_path

            if 'w' in style:
                psbt.outputs[i].witness_script = scr
                if style.endswith('p2sh'):
                    psbt.outputs[i].redeem_script = b'\0\x20' + hashlib.sha256(scr).digest()
            elif style.endswith('sh'):
                psbt.outputs[i].redeem_script = scr
        else:
            scriptPubKey = fake_dest_addr(style)

        assert scriptPubKey

        # if psbt_v2:
        #     psbt.outputs[i].script = scriptPubKey
        #     if outvals:
        #         psbt.outputs[i].amount = outvals[i]
        #     else:
        #         psbt.outputs[i].amount = int(round(((input_amount * num_ins) - fee) / num_outs, 4))


        if not outvals:
            h = CTxOut(int(round(((input_amount*num_ins)-fee) / num_outs, 4)), scriptPubKey)
        else:
            h = CTxOut(int(outvals[i]), scriptPubKey)

        txn.vout.append(h)

    psbt.txn = txn.serialize_with_witness()

    rv = BytesIO()
    psbt.serialize(rv)

    return rv.getvalue()

def render_address(script, testnet=True):
    # take a scriptPubKey (part of the TxOut) and convert into conventional human-readable
    # string... aka: the "payment address"
    from .segwit_addr import encode as bech32_encode

    ll = len(script)

    if not testnet:
        bech32_hrp = 'bc'
        b58_addr    = bytes([0])
        b58_script  = bytes([5])
        b58_privkey = bytes([128])
    else:
        bech32_hrp = 'tb'
        b58_addr    = bytes([111])
        b58_script  = bytes([196])
        b58_privkey = bytes([239])

    # P2PKH
    if ll == 25 and script[0:3] == b'\x76\xA9\x14' and script[23:26] == b'\x88\xAC':
        return encode_base58_checksum(b58_addr + script[3:3+20])

    # P2SH
    if ll == 23 and script[0:2] == b'\xA9\x14' and script[22] == 0x87:
        return encode_base58_checksum(b58_script + script[2:2+20])

    # P2WPKH
    if ll == 22 and script[0:2] == b'\x00\x14':
        return bech32_encode(bech32_hrp, 0, script[2:])

    # P2WSH, P2TR and later
    if ll == 34 and script[0] <= 16 and script[1] == 0x20:
        return bech32_encode(bech32_hrp, script[0], script[2:])

    raise ValueError('Unknown payment script', repr(script))

# EOF
