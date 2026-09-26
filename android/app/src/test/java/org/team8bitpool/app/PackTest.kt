package org.team8bitpool.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.team8bitpool.app.core.Pack
import org.team8bitpool.app.core.PackError
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/** Import accepts only an intact pack, and never writes outside its folder. */
class PackTest {
    @get:Rule val tmp = TemporaryFolder()
    private val packDir = File(Repo.root, "android/app/src/test/resources/pack")

    private fun zipOf(dir: File, edit: (String, ByteArray) -> ByteArray = { _, b -> b }, extra: Map<String, ByteArray> = emptyMap()): ByteArray {
        val out = ByteArrayOutputStream()
        ZipOutputStream(out).use { z ->
            dir.walkTopDown().filter { it.isFile }.forEach { f ->
                val name = f.relativeTo(dir).invariantSeparatorsPath
                z.putNextEntry(ZipEntry(name)); z.write(edit(name, f.readBytes())); z.closeEntry()
            }
            extra.forEach { (n, b) -> z.putNextEntry(ZipEntry(n)); z.write(b); z.closeEntry() }
        }
        return out.toByteArray()
    }

    private fun expectRefused(zip: ByteArray, why: String) {
        val root = tmp.newFolder()
        try { Pack.import(ByteArrayInputStream(zip), root); fail("imported a pack that $why") }
        catch (e: PackError) { assertTrue(!File(root, "current").exists()) }
    }

    @Test
    fun anIntactPackIsImported() {
        val root = tmp.newFolder()
        val p = Pack.import(ByteArrayInputStream(zipOf(packDir)), root)
        assertEquals(18, p.lessonsApi.getJSONArray("lessons").length())
    }

    @Test
    fun aChangedFileIsRefused() =
        expectRefused(zipOf(packDir, { n, b -> if (n == "translations.json") b + " ".toByteArray() else b }), "was changed")

    @Test
    fun anUnlistedFileIsRefused() = expectRefused(zipOf(packDir, extra = mapOf("extra.txt" to ByteArray(1))), "has an extra file")

    @Test
    fun aPathOutsideThePackIsRefused() = expectRefused(zipOf(packDir, extra = mapOf("../evil.txt" to ByteArray(1))), "escapes its folder")

    @Test
    fun aFailedImportKeepsThePreviousPack() {
        val root = tmp.newFolder()
        Pack.import(ByteArrayInputStream(zipOf(packDir)), root)
        try { Pack.import(ByteArrayInputStream(zipOf(packDir, extra = mapOf("x" to ByteArray(1)))), root) } catch (_: PackError) {}
        Pack.verify(File(root, "current"))
    }
}
