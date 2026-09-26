package org.team8bitpool.app.core

import java.math.BigInteger
import java.security.MessageDigest

/**
 * Ed25519 (RFC 8032), ported from the RFC's Python reference implementation
 * (RFC 8032 section 6; code components of RFCs are under the Simplified BSD
 * licence). Android 9's own security providers have no Ed25519 (it arrived in
 * API 33), so the tablet carries this small one. Not constant-time: it verifies
 * public data (pack signatures) and signs the tablet's own export; no private key is
 * processed on behalf of anyone else. Tested against RFC 8032 test vectors and
 * against Python's `cryptography` (Ed25519Test, tests/data/ed25519_vectors.json).
 */
object Ed25519 {
    private val TWO: BigInteger = BigInteger.valueOf(2)     // BigInteger.TWO is not in every Android version
    private val p: BigInteger = BigInteger.ONE.shiftLeft(255).subtract(BigInteger.valueOf(19))
    private val q: BigInteger = BigInteger.ONE.shiftLeft(252).add(BigInteger("27742317777372353535851937790883648493"))
    private fun inv(x: BigInteger) = x.modPow(p.subtract(TWO), p)
    private val d: BigInteger = BigInteger.valueOf(-121665).multiply(inv(BigInteger.valueOf(121666))).mod(p)
    private val sqrtM1: BigInteger = TWO.modPow(p.subtract(BigInteger.ONE).divide(BigInteger.valueOf(4)), p)

    private class Pt(val x: BigInteger, val y: BigInteger, val z: BigInteger, val t: BigInteger)

    private fun add(P: Pt, Q: Pt): Pt {
        val a = P.y.subtract(P.x).multiply(Q.y.subtract(Q.x)).mod(p)
        val b = P.y.add(P.x).multiply(Q.y.add(Q.x)).mod(p)
        val c = TWO.multiply(P.t).multiply(Q.t).multiply(d).mod(p)
        val dd = TWO.multiply(P.z).multiply(Q.z).mod(p)
        val e = b.subtract(a); val f = dd.subtract(c); val g = dd.add(c); val h = b.add(a)
        return Pt(e.multiply(f).mod(p), g.multiply(h).mod(p), f.multiply(g).mod(p), e.multiply(h).mod(p))
    }

    private fun mul(s0: BigInteger, P0: Pt): Pt {
        var s = s0; var P = P0
        var Q = Pt(BigInteger.ZERO, BigInteger.ONE, BigInteger.ONE, BigInteger.ZERO)
        while (s.signum() > 0) {
            if (s.testBit(0)) Q = add(Q, P)
            P = add(P, P)
            s = s.shiftRight(1)
        }
        return Q
    }

    private fun equal(P: Pt, Q: Pt) =
        P.x.multiply(Q.z).subtract(Q.x.multiply(P.z)).mod(p).signum() == 0 &&
            P.y.multiply(Q.z).subtract(Q.y.multiply(P.z)).mod(p).signum() == 0

    private fun recoverX(y: BigInteger, sign: Int): BigInteger? {
        if (y >= p) return null
        val x2 = y.multiply(y).subtract(BigInteger.ONE).multiply(inv(d.multiply(y).multiply(y).add(BigInteger.ONE))).mod(p)
        if (x2.signum() == 0) return if (sign != 0) null else BigInteger.ZERO
        var x = x2.modPow(p.add(BigInteger.valueOf(3)).divide(BigInteger.valueOf(8)), p)
        if (x.multiply(x).subtract(x2).mod(p).signum() != 0) x = x.multiply(sqrtM1).mod(p)
        if (x.multiply(x).subtract(x2).mod(p).signum() != 0) return null
        if ((if (x.testBit(0)) 1 else 0) != sign) x = p.subtract(x)
        return x
    }

    private val G: Pt by lazy {
        val gy = BigInteger.valueOf(4).multiply(inv(BigInteger.valueOf(5))).mod(p)
        val gx = recoverX(gy, 0)!!
        Pt(gx, gy, BigInteger.ONE, gx.multiply(gy).mod(p))
    }

    private fun le(b: ByteArray): BigInteger = BigInteger(1, b.reversedArray())
    private fun le32(x: BigInteger): ByteArray {
        val be = x.toByteArray().let { if (it.size > 32) it.copyOfRange(it.size - 32, it.size) else it }
        val out = ByteArray(32)
        for (i in be.indices) out[i] = be[be.size - 1 - i]
        return out
    }

    private fun compress(P: Pt): ByteArray {
        val zi = inv(P.z)
        val x = P.x.multiply(zi).mod(p); val y = P.y.multiply(zi).mod(p)
        return le32(if (x.testBit(0)) y.setBit(255) else y)
    }

    private fun decompress(s: ByteArray): Pt? {
        if (s.size != 32) return null
        var y = le(s)
        val sign = if (y.testBit(255)) 1 else 0
        y = y.clearBit(255)
        val x = recoverX(y, sign) ?: return null
        return Pt(x, y, BigInteger.ONE, x.multiply(y).mod(p))
    }

    private fun sha512(vararg parts: ByteArray): ByteArray {
        val md = MessageDigest.getInstance("SHA-512")
        for (b in parts) md.update(b)
        return md.digest()
    }

    private fun sha512ModQ(vararg parts: ByteArray) = le(sha512(*parts)).mod(q)

    private fun expand(seed: ByteArray): Pair<BigInteger, ByteArray> {
        require(seed.size == 32) { "Ed25519 private key must be 32 bytes" }
        val h = sha512(seed)
        var a = le(h.copyOfRange(0, 32))
        a = a.and(BigInteger.ONE.shiftLeft(254).subtract(BigInteger.valueOf(8))).or(BigInteger.ONE.shiftLeft(254))
        return a to h.copyOfRange(32, 64)
    }

    fun publicKey(seed: ByteArray): ByteArray = compress(mul(expand(seed).first, G))

    fun sign(seed: ByteArray, msg: ByteArray): ByteArray {
        val (a, prefix) = expand(seed)
        val pub = compress(mul(a, G))
        val r = sha512ModQ(prefix, msg)
        val rs = compress(mul(r, G))
        val h = sha512ModQ(rs, pub, msg)
        val s = r.add(h.multiply(a)).mod(q)
        return rs + le32(s)
    }

    fun verify(public: ByteArray, msg: ByteArray, signature: ByteArray): Boolean {
        if (public.size != 32 || signature.size != 64) return false
        val A = decompress(public) ?: return false
        val rs = signature.copyOfRange(0, 32)
        val R = decompress(rs) ?: return false
        val s = le(signature.copyOfRange(32, 64))
        if (s >= q) return false
        val h = sha512ModQ(rs, public, msg)
        return equal(mul(s, G), add(R, mul(h, A)))
    }

    fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }
    fun unhex(s: String): ByteArray = ByteArray(s.length / 2) { s.substring(2 * it, 2 * it + 2).toInt(16).toByte() }
}
