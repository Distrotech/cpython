"""HMAC (Keyed-Hashing for Message Authentication) Python module.

Implements the HMAC algorithm as described by RFC 2104.
"""

import warnings as _warnings

trans_5C = bytes((x ^ 0x5C) for x in range(256))
trans_36 = bytes((x ^ 0x36) for x in range(256))

# The size of the digests returned by HMAC depends on the underlying
# hashing module used.  Use digest_size from the instance of HMAC instead.
digest_size = None


def compare_digest(a, b):
    """Returns the equivalent of 'a == b', but avoids content based short
    circuiting to reduce the vulnerability to timing attacks."""
    # Consistent timing matters more here than data type flexibility
    if not (isinstance(a, bytes) and isinstance(b, bytes)):
        raise TypeError("inputs must be bytes instances")

    # We assume the length of the expected digest is public knowledge,
    # thus this early return isn't leaking anything an attacker wouldn't
    # already know
    if len(a) != len(b):
        return False

    # We assume that integers in the bytes range are all cached,
    # thus timing shouldn't vary much due to integer object creation
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


class HMAC:
    """RFC 2104 HMAC class.  Also complies with RFC 4231.

    This supports the API for Cryptographic Hash Functions (PEP 247).
    """
    blocksize = 64  # 512-bit HMAC; can be changed in subclasses.

    def __init__(self, key, msg = None, digestmod = None):
        """Create a new HMAC object.

        key:       key for the keyed hash object.
        msg:       Initial input for the hash, if provided.
        digestmod: A module supporting PEP 247.  *OR*
                   A hashlib constructor returning a new hash object.
                   Defaults to hashlib.md5.

        Note: key and msg must be bytes objects.
        """

        if not isinstance(key, bytes):
            raise TypeError("expected bytes, but got %r" % type(key).__name__)

        if digestmod is None:
            import hashlib
            digestmod = hashlib.md5

        if callable(digestmod):
            self.digest_cons = digestmod
        else:
            self.digest_cons = lambda d=b'': digestmod.new(d)

        self.outer = self.digest_cons()
        self.inner = self.digest_cons()
        self.digest_size = self.inner.digest_size

        if hasattr(self.inner, 'block_size'):
            blocksize = self.inner.block_size
            if blocksize < 16:
                _warnings.warn('block_size of %d seems too small; using our '
                               'default of %d.' % (blocksize, self.blocksize),
                               RuntimeWarning, 2)
                blocksize = self.blocksize
        else:
            _warnings.warn('No block_size attribute on given digest object; '
                           'Assuming %d.' % (self.blocksize),
                           RuntimeWarning, 2)
            blocksize = self.blocksize

        if len(key) > blocksize:
            key = self.digest_cons(key).digest()

        key = key + bytes(blocksize - len(key))
        self.outer.update(key.translate(trans_5C))
        self.inner.update(key.translate(trans_36))
        if msg is not None:
            self.update(msg)

    def update(self, msg):
        """Update this hashing object with the string msg.
        """
        if not isinstance(msg, bytes):
            raise TypeError("expected bytes, but got %r" % type(msg).__name__)
        self.inner.update(msg)

    def copy(self):
        """Return a separate copy of this hashing object.

        An update to this copy won't affect the original object.
        """
        # Call __new__ directly to avoid the expensive __init__.
        other = self.__class__.__new__(self.__class__)
        other.digest_cons = self.digest_cons
        other.digest_size = self.digest_size
        other.inner = self.inner.copy()
        other.outer = self.outer.copy()
        return other

    def _current(self):
        """Return a hash object for the current state.

        To be used only internally with digest() and hexdigest().
        """
        h = self.outer.copy()
        h.update(self.inner.digest())
        return h

    def digest(self):
        """Return the hash value of this hashing object.

        This returns a string containing 8-bit data.  The object is
        not altered in any way by this function; you can continue
        updating the object after calling this function.
        """
        h = self._current()
        return h.digest()

    def hexdigest(self):
        """Like digest(), but returns a string of hexadecimal digits instead.
        """
        h = self._current()
        return h.hexdigest()

def new(key, msg = None, digestmod = None):
    """Create a new hashing object and return it.

    key: The starting key for the hash.
    msg: if available, will immediately be hashed into the object's starting
    state.

    You can now feed arbitrary strings into the object using its update()
    method, and can ask for the hash value at any time by calling its digest()
    method.
    """
    return HMAC(key, msg, digestmod)
