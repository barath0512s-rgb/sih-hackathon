package org.team8bitpool.app

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.team8bitpool.app.core.Api
import org.team8bitpool.app.core.Engines
import org.team8bitpool.app.core.Pack
import org.team8bitpool.app.core.Resp
import org.team8bitpool.app.core.Store
import java.io.File

/**
 * The tablet's API meets contract/rest_contract.json, the same file the hub is
 * tested against (tests/test_contract.py). Kotlin port of contract/runner.py.
 * Uses the test pack in src/test/resources/pack (tools/build_content_pack.py --no-audio).
 */
class ContractTest {
    @get:Rule val tmp = TemporaryFolder()

    private val packDir = File(Repo.root, "android/app/src/test/resources/pack")

    private fun api(engines: Engines = Engines()): Api {
        val pack = Pack(packDir)
        return Api({ pack }, Store(tmp.newFolder("store")), engines)
    }

    @Test
    fun theTabletMeetsTheContract() {
        val failures = run(api())
        assertTrue(failures.joinToString("\n"), failures.isEmpty())
    }

    @Test
    fun theTestPackIsIntact() {
        Pack.verify(packDir)
    }

    @Test
    fun aTeacherCorrectionIsReused() {
        val a = api()
        val line = Pack(packDir).lessonsApi.getJSONArray("lessons").getJSONObject(0)
            .getJSONArray("plan").getJSONObject(0).getString("hindi")
        post(a, "/feedback", JSONObject().put("hindi_text", line).put("santali_text", "x")
            .put("corrected_text", "ᱥᱟᱹᱨᱤ").put("direction", "hi-to-sat"))
        val r = JSONObject(String(post(a, "/translate/text", JSONObject().put("text", "$line ").put("direction", "hi-to-sat")).body))
        assertEquals("ᱥᱟᱹᱨᱤ", r.getString("translated_text"))
        assertEquals("teacher", r.getString("source"))
    }

    private fun post(a: Api, path: String, body: JSONObject): Resp =
        a.handle("POST", path, emptyMap(), body.toString().toByteArray(), "application/json")

    // ── the runner (contract/runner.py) ──────────────────────────────────────
    private fun run(a: Api, engines: Set<String> = emptySet()): List<String> {
        val c = JSONObject(File(Repo.root, "contract/rest_contract.json").readText())
        val cases = c.getJSONArray("setup").toList() + c.getJSONArray("cases").toList()
        val saved = HashMap<String, Any>()
        val failures = mutableListOf<String>()
        for (case in cases) {
            val id = case.getString("id")
            val body = try { case.opt("json")?.takeIf { it != JSONObject.NULL }?.let { fill(it, saved) as JSONObject } }
                       catch (e: NoSuchElementException) { failures += "$id: needs ${e.message}"; continue }
            val path = fill(case.getString("path"), saved) as String
            val (p, q) = path.split("?", limit = 2).let { it[0] to (it.getOrNull(1) ?: "") }
            val query = q.split("&").filter { "=" in it }.associate { it.substringBefore("=") to it.substringAfter("=") }
            val r = a.handle(case.getString("method"), p, query, body?.toString()?.toByteArray(),
                if (body != null) "application/json" else null)
            val raw = String(r.body, Charsets.UTF_8)
            val needs = case.optJSONArray("needs")?.let { n -> (0 until n.length()).map { n.getString(it) } } ?: emptyList()
            if (needs.any { it !in engines }) {
                val j = runCatching { JSONObject(raw) }.getOrNull()
                if (r.status != 503 || j?.optString("code") != "engine_not_on_device")
                    failures += "$id: needs $needs, so expected 503 engine_not_on_device, got ${r.status} ${raw.take(120)}"
                continue
            }
            val want = case.optInt("status", 200)
            if (r.status != want) { failures += "$id: status ${r.status}, expected $want: ${raw.take(160)}"; continue }
            if (case.has("content_type")) {
                if (!r.type.startsWith(case.getString("content_type"))) failures += "$id: content type ${r.type}"
                continue
            }
            val j = runCatching { JSONObject(raw) }.getOrNull()
            if (j == null) { failures += "$id: not a JSON object: ${raw.take(120)}"; continue }
            case.optJSONObject("types")?.let { types ->
                for (k in types.keys()) {
                    val v = get(j, k)
                    if (v === MISSING) failures += "$id: missing $k"
                    else if (!typeOk(v, types.getString(k))) failures += "$id: $k is ${v?.javaClass?.simpleName}, expected ${types.getString(k)}"
                }
            }
            case.optJSONObject("equals")?.let { eq ->
                for (k in eq.keys()) if (get(j, k).toString() != eq.get(k).toString()) failures += "$id: $k = ${get(j, k)}, expected ${eq.get(k)}"
            }
            case.optJSONObject("save")?.let { sv ->
                for (name in sv.keys()) {
                    val v = get(j, sv.getString(name))
                    if (v === MISSING) failures += "$id: cannot save $name" else saved[name] = v!!
                }
            }
        }
        return failures
    }

    private object MISSING

    private fun get(o: Any?, dotted: String): Any? {
        var cur: Any? = o
        for (part in dotted.split(".")) {
            cur = when (cur) {
                is JSONArray -> part.toIntOrNull()?.takeIf { it < cur.length() }?.let { cur.get(it) } ?: return MISSING
                is JSONObject -> if (cur.has(part)) cur.get(part) else return MISSING
                else -> return MISSING
            }
        }
        return cur
    }

    private fun typeOk(v: Any?, spec: String) = spec.split("|").any { t ->
        when (t) {
            "str" -> v is String
            "int" -> v is Int || v is Long
            "num" -> v is Number
            "bool" -> v is Boolean
            "list" -> v is JSONArray
            "dict" -> v is JSONObject
            "null" -> v == null || v == JSONObject.NULL
            else -> false
        }
    }

    private fun fill(v: Any, saved: Map<String, Any>): Any = when (v) {
        is String -> Regex("^\\{(\\w+)\\}$").matchEntire(v)?.let { saved[it.groupValues[1]] ?: throw NoSuchElementException(it.groupValues[1]) }
            ?: Regex("\\{(\\w+)\\}").replace(v) { m -> (saved[m.groupValues[1]] ?: throw NoSuchElementException(m.groupValues[1])).toString() }
        is JSONObject -> JSONObject().also { o -> for (k in v.keys()) o.put(k, fill(v.get(k), saved)) }
        is JSONArray -> JSONArray().also { a -> for (i in 0 until v.length()) a.put(fill(v.get(i), saved)) }
        else -> v
    }

    private fun JSONArray.toList() = (0 until length()).map { getJSONObject(it) }
}
