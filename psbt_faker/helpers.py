import struct, hashlib
from .ripemd import ripemd160

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
    return struct.pack('>I', xfp).hex().upper()

def str2path(xfp, s):
    # output binary needed for BIP-174
    p = list(str2ipath(s))
    return bytes.fromhex(xfp) + struct.pack('<%dI' % (len(p)), *p)

def hash160(data):
    return ripemd160(hashlib.sha256(data).digest())