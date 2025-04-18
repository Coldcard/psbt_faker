#
# Creating fake transactions. Not simple... but only for testing purposes, so ....
#
import struct, random, hashlib
from io import BytesIO
from .segwit_addr import encode as bech32_encode
from .psbt import BasicPSBT, BasicPSBTInput, BasicPSBTOutput
from .base58 import encode_base58_checksum
from .helpers import str2path, hash160
from .serialize import uint256_from_str
from .bip32 import BIP32Node
from .ctransaction import CTransaction, CTxIn, CTxOut, COutPoint

# all possible addr types, including multisig/scripts
# single-signer
ADDR_STYLES_SINGLE = ['p2wpkh', 'p2pkh', 'p2wpkh-p2sh', 'p2sh-p2wpkh', 'p2tr']
# multi-signer
ADDR_STYLES_MULTI = ['p2wsh', 'p2sh', 'p2sh-p2wsh', 'p2wsh-p2sh']

ADDR_STYLES = ADDR_STYLES_MULTI + ADDR_STYLES_SINGLE

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

    if style in ['p2sh', 'p2wsh-p2sh', 'p2wpkh-p2sh', 'p2sh-p2wsh', 'p2sh-p2wpkh']:
        # all equally bogus P2SH outputs
        return bytes([0xa9, 0x14]) + prandom(20) + bytes([0x87])

    if style == 'p2pkh':
        return bytes([0x76, 0xa9, 0x14]) + prandom(20) + bytes([0x88, 0xac])

    # missing: if style == 'p2pk' =>  pay to pubkey, considered obsolete

    raise ValueError('not supported: ' + style)

def make_change_addr(master_xfp, orig_der,  account_key, idx, style):
    # provide script, pubkey and xpath for a legit-looking change output

    redeem_scr, actual_scr = None, None

    if orig_der:
        path = str2path(master_xfp, f"{orig_der}/0/{idx}")
    else:
        path = str2path(master_xfp, f"0/{idx}")

    dest = account_key.subkey_for_path(f"0/{idx}")

    target = dest.hash160()
    assert len(target) == 20

    is_segwit = False
    if style == 'p2pkh':
        redeem_scr = bytes([0x76, 0xa9, 0x14]) + target + bytes([0x88, 0xac])
    elif style == 'p2wpkh':
        redeem_scr = bytes([0, 20]) + target
        is_segwit = True
    elif style in ('p2wpkh-p2sh', 'p2sh-p2wpkh'):
        redeem_scr = bytes([0, 20]) + target
        actual_scr = bytes([0xa9, 0x14]) + hash160(redeem_scr) + bytes([0x87])
    else:
        raise ValueError('cant make fake change output of type: ' + style)

    return redeem_scr, actual_scr, is_segwit, dest.sec(), path


def fake_txn(num_ins, num_outs, master_xpub=None, subpath="0/%d", fee=10000,
         outvals=None, segwit_in=False, wrapped=False, outstyles=None,
         change_outputs=[], op_return=None, psbt_v2=None, input_amount=1E8,
         locktime=0, sequences=None, is_testnet=False, partial=False):

    psbt = BasicPSBT()

    if psbt_v2:
        psbt.version = 2
        psbt.txn_version = 2
        psbt.input_count = num_ins
        psbt.output_count = num_outs
        psbt.fallback_locktime = locktime

    txn = CTransaction()
    txn.nVersion = 2
    txn.nLockTime = locktime

    # we have a key; use it to provide "plausible" value inputs
    if master_xpub:
        mk = BIP32Node.from_wallet_key(master_xpub)
        xfp = mk.fingerprint()
    else:
        # special value for COLDCARD: zero xfp => anyone can try to sign
        mk = BIP32Node.from_master_secret(b'1' * 32)
        xfp = bytes(4)

    psbt.inputs = [BasicPSBTInput(idx=i) for i in range(num_ins)]
    psbt.outputs = [BasicPSBTOutput(idx=i) for i in range(num_outs)]

    outputs = []

    assert subpath[0:2] == '0/'

    af = ("p2sh-p2wpkh" if wrapped else "p2wpkh") if segwit_in else "p2pkh"
    try:
        assert mk.privkey() is not None
        # user provided extended private key, we can simulate proper hardened derivations
        if af == "p2wpkh":
            purpose = 84
        elif af == "p2sh-p2wpkh":
            purpose = 49
        else:
            purpose = 44

        orig_der = f"{purpose}h/{int(is_testnet)}h/0h"
        account_key = mk.subkey_for_path(orig_der)
    except:
        # we cannot proceed to hardened derivation as we only have extended pubkey
        account_key = mk
        orig_der = None

    for i in range(num_ins):
        # make a fake txn to supply each of the inputs
        # addr where the fake money will be stored.
        # always from internal address chain
        subder = f"1/{i}"
        subkey = account_key.subkey_for_path(subder)
        sec = subkey.sec()
        assert len(sec) == 33, "expect compressed"

        if partial and (i == 0):
            psbt.inputs[i].bip32_paths[sec] = b'Nope' + struct.pack('<II', 1, i)
        else:
            if orig_der:
                dp = str2path(xfp.hex(), f"{orig_der}/{subder}")
            else:
                dp = str2path(xfp.hex(), subder)

            psbt.inputs[i].bip32_paths[sec] = dp

        # UTXO that provides the funding for to-be-signed txn
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
            if wrapped:
                # p2sh-p2wpkh
                psbt.inputs[i].redeem_script = scr
                scr = bytes([0xa9, 0x14]) + hash160(scr) + bytes([0x87])
        else:
            # p2pkh
            scr = bytes([0x76, 0xa9, 0x14]) + subkey.hash160() + bytes([0x88, 0xac])

        supply.vout.append(CTxOut(int(input_amount), scr))

        if segwit_in:
            # just utxo for segwit
            psbt.inputs[i].witness_utxo = supply.vout[-1].serialize()
        else:
            # whole tx for pre-segwit
            psbt.inputs[i].utxo = supply.serialize_with_witness()

        supply.calc_sha256()

        seq = None
        if sequences:
            # custom provided properly encoded sequence numbers
            try:
                seq = sequences[i]
            except: pass

        if seq is None:
            seq = 0xffffffff
            if locktime and (i == 0):
                # decrement one sequence to enable nLockTime enforcement
                seq = 0xfffffffe

        if psbt_v2:
            psbt.inputs[i].previous_txid = supply.hash
            psbt.inputs[i].prevout_idx = 0
            psbt.inputs[i].sequence = seq
            if locktime:
                # no need to do this as fallback locktime is already set in globals but yolo
                if locktime < 500000000:
                    psbt.inputs[i].req_height_locktime = locktime
                else:
                    psbt.inputs[i].req_time_locktime = locktime


        spendable = CTxIn(COutPoint(supply.sha256, 0), nSequence=seq)
        txn.vin.append(spendable)

    for i in range(num_outs):
        if not outstyles:
            style = af
        elif len(outstyles) == 1:
            style = outstyles[0]
        elif len(outstyles) == num_outs:
            style = outstyles[i]
        else:
            style = outstyles[i % len(outstyles)]

        if i in change_outputs:
            scr, act_scr, isw, pubkey, sp = make_change_addr(mk.fingerprint().hex(), orig_der,
                                                             account_key, i, style)

            if len(pubkey) == 32:  # xonly
                psbt.outputs[i].taproot_bip32_paths[pubkey] = sp
            else:
                psbt.outputs[i].bip32_paths[pubkey] = sp

        else:
            scr = act_scr = fake_dest_addr(style)
            isw = ('w' in style)

        assert scr
        act_scr = act_scr or scr

        # one of these is not needed anymore in v2 as you have scriptPubkey provided by self.script
        if "p2sh" in style:  # in ('p2sh-p2wpkh', 'p2wpkh-p2sh'):
            psbt.outputs[i].redeem_script = scr
        elif isw:
            psbt.outputs[i].witness_script = scr

        if psbt_v2:
            psbt.outputs[i].script = act_scr
            psbt.outputs[i].amount = int(
                outvals[i] if outvals else round(((input_amount * num_ins) - fee) / num_outs, 4))

        if not outvals:
            h = CTxOut(int(round(((input_amount * num_ins) - fee) / num_outs, 4)), act_scr)
        else:
            h = CTxOut(int(outvals[i]), act_scr)

        outputs.append((h.nValue, act_scr, (i in change_outputs)))

        txn.vout.append(h)

    # op_return is a tuple of (amount, data)
    if op_return:
        for op_ret in op_return:
            amount, data = op_ret
            op_return_size = len(data)
            if op_return_size < 76:
                script = bytes([106, op_return_size]) + data
            else:
                script = bytes([106, 76, op_return_size]) + data

            op_ret_o = BasicPSBTOutput(idx=len(psbt.outputs))
            if psbt_v2:
                op_ret_o.script = script
                op_ret_o.amount = amount
                psbt.output_count += 1
            else:
                op_return_out = CTxOut(amount, script)
                txn.vout.append(op_return_out)

            psbt.outputs.append(op_ret_o)

    if not psbt_v2:
        psbt.txn = txn.serialize_with_witness()

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
                outstyles=['p2wsh'], change_outputs=[], incl_xpubs=False, psbt_v2=False,
                input_amount=1E8, bip67=True, locktime=0, wrapped=False,
                sequences=None, is_testnet=False, change_af=None):
    # make various size MULTISIG txn's ... completely fake and pointless values
    # - but has UTXO's to match needs
    # spending change outputs
    psbt = BasicPSBT()

    if psbt_v2:
        psbt.version = 2
        psbt.txn_version = 2
        psbt.input_count = num_ins
        psbt.output_count = num_outs
        psbt.fallback_locktime = locktime

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
        # always same address format as config defines
        addr, scriptPubKey, script, details = make_ms_address(M, keys, i, True,
                                                              addr_fmt=change_af,
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

        seq = None
        if sequences:
            # custom provided properly encoded sequence numbers
            try:
                seq = sequences[i]
            except: pass

        if seq is None:
            seq = 0xffffffff
            if locktime and (i == 0):
                # decrement one sequence to enable nLockTime enforcement
                # only on 0th input
                seq = 0xfffffffe

        if psbt_v2:
            psbt.inputs[i].previous_txid = supply.hash
            psbt.inputs[i].prevout_idx = 0
            psbt.inputs[i].sequence = seq
            if locktime:
                # no need to do this as fallback locktime is already set in globals but yolo
                if locktime < 500000000:
                    psbt.inputs[i].req_height_locktime = locktime
                else:
                    psbt.inputs[i].req_time_locktime = locktime

        spendable = CTxIn(COutPoint(supply.sha256, 0), nSequence=seq)
        txn.vin.append(spendable)

    outputs = []
    for i in range(num_outs):
        if i in change_outputs:
            # change outputs are always same as multisig address format
            addr, scriptPubKey, scr, details = make_ms_address(M, keys, num_ins+i, False,
                                                               addr_fmt=change_af, bip67=bip67)

            for pubkey, xfp_path in details:
                psbt.outputs[i].bip32_paths[pubkey] = xfp_path

            if 'w' in change_af:
                psbt.outputs[i].witness_script = scr
                if change_af.endswith('p2sh'):
                    psbt.outputs[i].redeem_script = b'\0\x20' + hashlib.sha256(scr).digest()
            elif change_af.endswith('sh'):
                psbt.outputs[i].redeem_script = scr
        else:
            if not outstyles:
                # make same outstyles as instyles
                style = change_af
            elif len(outstyles) == 1:
                style = outstyles[0]
            elif len(outstyles) == num_outs:
                style = outstyles[i-len(change_outputs)]
            else:
                style = outstyles[(i-len(change_outputs)) % len(outstyles)]

            scriptPubKey = fake_dest_addr(style)

        assert scriptPubKey

        if psbt_v2:
            psbt.outputs[i].script = scriptPubKey
            if outvals:
                psbt.outputs[i].amount = outvals[i]
            else:
                psbt.outputs[i].amount = int(round(((input_amount * num_ins) - fee) / num_outs, 4))


        if not outvals:
            h = CTxOut(int(round(((input_amount*num_ins)-fee) / num_outs, 4)), scriptPubKey)
        else:
            h = CTxOut(int(outvals[i]), scriptPubKey)

        txn.vout.append(h)

        outputs.append((h.nValue, scriptPubKey, (i in change_outputs)))

    if not psbt_v2:
        psbt.txn = txn.serialize_with_witness()

    rv = BytesIO()
    psbt.serialize(rv)

    return rv.getvalue(), [(n, render_address(s, is_testnet), ic) for n,s,ic in outputs]

def render_address(script, testnet=True):
    # take a scriptPubKey (part of the TxOut) and convert into conventional human-readable
    # string... aka: the "payment address"
    from .segwit_addr import encode as bech32_encode

    ll = len(script)

    if not testnet:
        bech32_hrp = 'bc'
        b58_addr    = bytes([0])
        b58_script  = bytes([5])
    else:
        bech32_hrp = 'tb'
        b58_addr    = bytes([111])
        b58_script  = bytes([196])

    # P2PKH
    if ll == 25 and script[0:3] == b'\x76\xA9\x14' and script[23:26] == b'\x88\xAC':
        return encode_base58_checksum(b58_addr + script[3:3+20])

    # P2SH
    if ll == 23 and script[0:2] == b'\xA9\x14' and script[22] == 0x87:
        return encode_base58_checksum(b58_script + script[2:2+20])

    # segwit v0 (P2WPKH, P2WSH)
    if script[0] == 0 and script[1] in (0x14, 0x20) and (ll - 2) == script[1]:
        return bech32_encode(bech32_hrp, script[0], script[2:])

    # segwit v1 (P2TR) and later segwit version OP_1 .. OP_16
    if ll == 34 and (81 <= script[0] <= 96) and script[1] == 0x20:
        return bech32_encode(bech32_hrp, script[0] - 80, script[2:])

    raise ValueError('Unknown payment script', repr(script))

# EOF
