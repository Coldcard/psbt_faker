#
# Creating fake transactions. Not simple... but only for testing purposes, so ....
#
import time, os, random
from binascii import b2a_hex, a2b_hex
from io import BytesIO
from pprint import pprint, pformat
from decimal import Decimal
from pycoin.key.BIP32Node import BIP32Node
from .psbt import BasicPSBT, BasicPSBTInput, BasicPSBTOutput, PSBT_IN_REDEEM_SCRIPT

# all possible addr types, including multisig/scripts
ADDR_STYLES = ['p2wpkh', 'p2wsh', 'p2sh', 'p2pkh', 'p2wsh-p2sh', 'p2wpkh-p2sh', 'p2tr']

# single-signer
ADDR_STYLES_SINGLE = ['p2wpkh', 'p2pkh', 'p2wpkh-p2sh']

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
    import struct, random
    from pycoin.encoding import hash160

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
    from pycoin.tx.Tx import Tx
    from pycoin.tx.TxIn import TxIn
    from pycoin.tx.TxOut import TxOut
    from pycoin.serialize import h2b_rev
    from struct import pack

    psbt = BasicPSBT()
    txn = Tx(2,[],[])
    
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

        # UTXO that provides the funding for to-be-signed txn
        supply = Tx(2,[TxIn(pack('4Q', 0xdead, 0xbeef, 0, 0), 73)],[])

        scr = bytes([0x76, 0xa9, 0x14]) + subkey.hash160() + bytes([0x88, 0xac])

        supply.txs_out.append(TxOut(1E8, scr))

        with BytesIO() as fd:
            if not segwit_in:
                supply.stream(fd)
                psbt.inputs[i].utxo = fd.getvalue()
            else:
                supply.txs_out[-1].stream(fd)
                psbt.inputs[i].witness_utxo = fd.getvalue()

        spendable = TxIn(supply.hash(), 0)
        txn.txs_in.append(spendable)


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
            h = TxOut(round(((1E8*num_ins)-fee) / num_outs, 4), act_scr)
        else:
            h = TxOut(outvals[i], act_scr)

        outputs.append( (Decimal(h.coin_value)/Decimal(1E8), act_scr, is_change) )

        txn.txs_out.append(h)

    with BytesIO() as b:
        txn.stream(b)
        psbt.txn = b.getvalue()

    rv = BytesIO()
    psbt.serialize(rv)

    return rv.getvalue(), [(n, render_address(s, is_testnet), ic) for n,s,ic in outputs]
                                 

def render_address(script, testnet=True):
    # take a scriptPubKey (part of the TxOut) and convert into conventional human-readable
    # string... aka: the "payment address"
    from pycoin.encoding import b2a_hashed_base58
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
        return b2a_hashed_base58(b58_addr + script[3:3+20])

    # P2SH
    if ll == 23 and script[0:2] == b'\xA9\x14' and script[22] == 0x87:
        return b2a_hashed_base58(b58_script + script[2:2+20])

    # P2WPKH
    if ll == 22 and script[0:2] == b'\x00\x14':
        return bech32_encode(bech32_hrp, 0, script[2:])

    # P2WSH, P2TR and later
    if ll == 34 and script[0] <= 16 and script[1] == 0x20:
        return bech32_encode(bech32_hrp, script[0], script[2:])

    raise ValueError('Unknown payment script', repr(script))

# EOF
