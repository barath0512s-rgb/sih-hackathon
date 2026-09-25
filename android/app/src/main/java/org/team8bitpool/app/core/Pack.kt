package org.team8bitpool.app.core

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.InputStream
import java.security.MessageDigest
import java.util.zip.ZipInputStream

class PackError(message: String) : Exception(message)

/**
 * A content pack built by tools/build_content_pack.py, unpacked in a directory.
 * Only a pack whose files all match manifest.json is ever made current.
 */
class Pack(val dir: File) {
    val manifest: JSONObject = json("manifest.json")
    val config: JSONObject = json("api/config.json")
    val lessonsApi: JSONObject = json("api/lessons.json")
    val flashcardsApi: JSONObject = json("api/flashcards.json")
    private val lessons: JSONArray = JSONArray(File(dir, "lessons.json").readText())
    private val translations: JSONObject = json("translations.json")
    private val audio: JSONObject = json("audio/index.json")

    private fun json(rel: String) = JSONObject(File(dir, rel).readText())

    fun lesson(grade: String, topic: String): JSONObject? {
        for (i in 0 until lessons.length()) {
            val l = lessons.getJSONObject(i)
            if (l.getString("grade") == grade && l.getString("topic") == topic) return l.getJSONObject("lesson")
        }
        return null
    }

    /** The pack's translation of `text` ({text, source, review_status}) or null. */
    fun translation(text: String, direction: String): JSONObject? =
        translations.optJSONObject(direction)?.optJSONObject(TextNorm.key(text))

    /** The pack's audio file for exactly this line, or null. */
    fun audioFile(text: String, lang: String): File? {
        val name = audio.optJSONObject(lang)?.optString(text.trim(), "") ?: ""
        if (name.isEmpty() || !name.matches(Regex("[0-9a-f]{40}\\.wav"))) return null
        return File(dir, "audio/$name").takeIf { it.isFile }
    }

    fun worksheet(grade: String, topic: String): File? =
        File(dir, "worksheets/${grade}_$topic.pdf").takeIf { it.isFile && it.parentFile == File(dir, "worksheets") }

    companion object {
        const val FORMAT = 1

        /** Unzip into `work`, check every file against the manifest, then swap it in as `current`. */
        fun import(zip: InputStream, root: File): Pack {
            val work = File(root, "incoming")
            work.deleteRecursively(); work.mkdirs()
            ZipInputStream(zip).use { z ->
                while (true) {
                    val e = z.nextEntry ?: break
                    val out = File(work, e.name).canonicalFile
                    if (!out.path.startsWith(work.canonicalPath + File.separator)) throw PackError("bad path in pack: ${e.name}")
                    if (e.isDirectory) { out.mkdirs(); continue }
                    out.parentFile.mkdirs()
                    out.outputStream().use { z.copyTo(it) }
                }
            }
            verify(work)
            val current = File(root, "current")
            val old = File(root, "previous")
            old.deleteRecursively()
            if (current.exists() && !current.renameTo(old)) throw PackError("cannot replace the current pack")
            if (!work.renameTo(current)) { old.renameTo(current); throw PackError("cannot install the pack") }
            old.deleteRecursively()
            return Pack(current)
        }

        fun verify(dir: File) {
            val mf = File(dir, "manifest.json")
            if (!mf.isFile) throw PackError("not a content pack: no manifest.json")
            val m = JSONObject(mf.readText())
            if (m.optInt("format") != FORMAT) throw PackError("pack format ${m.optInt("format")}, this app reads $FORMAT")
            val files = m.getJSONObject("files")
            val listed = files.keys().asSequence().toSet()
            val present = dir.walkTopDown().filter { it.isFile }
                .map { it.relativeTo(dir).invariantSeparatorsPath }.filter { it != "manifest.json" }.toSet()
            (present - listed).firstOrNull()?.let { throw PackError("file not in the manifest: $it") }
            for (name in listed) {
                val f = File(dir, name)
                if (!f.isFile) throw PackError("missing from the pack: $name")
                if (sha256(f) != files.getString(name)) throw PackError("changed since the pack was built: $name")
            }
        }

        fun sha256(f: File): String {
            val md = MessageDigest.getInstance("SHA-256")
            f.inputStream().use { s ->
                val buf = ByteArray(1 shl 16)
                while (true) { val n = s.read(buf); if (n < 0) break; md.update(buf, 0, n) }
            }
            return md.digest().joinToString("") { "%02x".format(it) }
        }
    }
}
