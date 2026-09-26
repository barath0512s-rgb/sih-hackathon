package org.team8bitpool.app

import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.team8bitpool.app.core.Api
import org.team8bitpool.app.core.Ed25519
import org.team8bitpool.app.core.Pack
import org.team8bitpool.app.core.PackError
import org.team8bitpool.app.core.Store
import java.io.File

/** A4: Ed25519 (the port must match Python byte for byte), signed packs, and the tablet's signed export. */
class SyncTest {
    @get:Rule val tmp = TemporaryFolder()
    private val packDir = File(Repo.root, "android/app/src/test/resources/pack")
    private val hubKey = Ed25519.unhex(File(Repo.root, "android/app/src/main/assets/pack_signing.pub").readText().trim())

    @Test
    fun ed25519MatchesRfc8032AndPython() {
        val v = JSONObject(File(Repo.root, "tests/data/ed25519_vectors.json").readText()).getJSONArray("vectors")
        for (i in 0 until v.length()) {
            val c = v.getJSONObject(i)
            val seed = Ed25519.unhex(c.getString("seed")); val msg = Ed25519.unhex(c.getString("message"))
            assertEquals("public #$i", c.getString("public"), Ed25519.hex(Ed25519.publicKey(seed)))
            assertEquals("signature #$i", c.getString("signature"), Ed25519.hex(Ed25519.sign(seed, msg)))
            assertTrue(Ed25519.verify(Ed25519.unhex(c.getString("public")), msg, Ed25519.unhex(c.getString("signature"))))
            val bad = msg + byteArrayOf(1)
            assertFalse(Ed25519.verify(Ed25519.unhex(c.getString("public")), bad, Ed25519.unhex(c.getString("signature"))))
        }
    }

    private fun copyPack(): File {
        val d = tmp.newFolder(); packDir.copyRecursively(d, overwrite = true); return d
    }

    @Test
    fun aSignedPackIsAcceptedAndATamperedOneRefused() {
        Pack.trustedKey = hubKey
        try {
            Pack.verify(packDir)                                              // the committed test pack is signed
            val changed = copyPack()
            val mf = File(changed, "manifest.json")
            mf.writeText(mf.readText().replace("\"format\": 1", "\"format\": 1 "))   // same meaning, other bytes
            assertTrue(runCatching { Pack.verify(changed) }.exceptionOrNull() is PackError)
            val unsigned = copyPack(); File(unsigned, "manifest.sig").delete()
            val e = runCatching { Pack.verify(unsigned) }.exceptionOrNull()
            assertTrue(e is PackError && e.message!!.contains("not signed"))
            val otherKey = copyPack()
            File(otherKey, "manifest.sig").writeText(Ed25519.hex(Ed25519.sign(ByteArray(32) { 7 }, File(otherKey, "manifest.json").readBytes())))
            assertTrue(runCatching { Pack.verify(otherKey) }.exceptionOrNull() is PackError)
        } finally { Pack.trustedKey = null }
    }

    @Test
    fun theExportIsSignedAndHoldsOnlyCorrectionsAndCounts() {
        val pack = Pack(packDir)
        val store = Store(tmp.newFolder("store"))
        val exportDir = tmp.newFolder("export")
        val api = Api({ pack }, store, exportDir = exportDir)
        val s = JSONObject(String(api.handle("POST", "/session/start", emptyMap(),
            JSONObject().put("grade", "1").put("topic", "counting_1_10").toString().toByteArray(), "application/json").body))
        api.handle("POST", "/session/response", emptyMap(),
            JSONObject().put("session_id", s.getString("session_id")).put("step", 3).put("response", "ᱯᱮ").toString().toByteArray(), "application/json")
        api.handle("POST", "/feedback", emptyMap(), JSONObject().put("hindi_text", "दो आम").put("santali_text", "ᱵᱟᱨ ᱟᱢ")
            .put("direction", "hi-to-sat").put("is_correct", false).put("corrected_text", "ᱵᱟᱨᱭᱟ ᱟᱢ").toString().toByteArray(), "application/json")
        val r = JSONObject(String(api.handle("POST", "/sync/export", emptyMap(), null, null).body))
        assertEquals(1, r.getInt("corrections")); assertEquals(1, r.getInt("class_rows"))
        val file = File(r.getString("saved_to"))
        assertTrue(file.isFile)
        val outer = JSONObject(file.readText())
        val payload = outer.getString("payload")
        assertTrue(Ed25519.verify(Ed25519.unhex(outer.getString("public_key")), payload.toByteArray(), Ed25519.unhex(outer.getString("signature"))))
        val p = JSONObject(payload)
        assertEquals(store.deviceId, p.getString("device_id"))
        val row = p.getJSONArray("analytics").getJSONObject(0)
        assertEquals(1, row.getInt("sessions")); assertEquals(1, row.getInt("green"))
        assertFalse(payload.contains("audio") || payload.contains("name\""))
        // the tablet keeps its key: a second export has the same device id and key
        val again = JSONObject(String(api.handle("POST", "/sync/export", emptyMap(), null, null).body))
        assertEquals(r.getString("device_id"), again.getString("device_id"))
        assertArrayEquals(store.publicKey, Store(File(tmp.root, "store")).publicKey)
        // A8: the same counts per Lakshya and ISO week, as CSV
        val csv = String(api.handle("GET", "/progress/lakshya", mapOf("format" to "csv"), null, null).body).trim().lines()
        assertEquals("week,lakshya_id,lessons_taught,green,yellow,red,green_share,sources", csv[0])
        assertTrue(csv.drop(1).any { it.contains(",NIPUN-G1-NUM-1,1,1,0,0,1.0,") })
        assertEquals(404, api.handle("GET", "/progress/lakshya", mapOf("format" to "pdf"), null, null).status)
    }
}
