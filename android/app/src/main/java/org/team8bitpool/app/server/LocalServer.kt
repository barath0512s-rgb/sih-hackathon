package org.team8bitpool.app.server

import android.content.res.AssetManager
import fi.iki.elonen.NanoHTTPD
import org.team8bitpool.app.core.Api
import java.io.ByteArrayInputStream
import java.io.FileNotFoundException

/**
 * The hub's REST API on 127.0.0.1:5000, so frontend.html runs unchanged in the
 * WebView. Bound to the loopback address only: nothing else on the network can
 * reach it.
 */
class LocalServer(private val assets: AssetManager, private val api: Api, port: Int = PORT) :
    NanoHTTPD("127.0.0.1", port) {

    override fun serve(session: IHTTPSession): Response {
        val path = session.uri
        if (session.method == Method.GET && (path == "/" || path == "/index.html")) return asset("web/frontend.html", "text/html; charset=utf-8")
        if (session.method == Method.GET && path.startsWith("/static/")) {
            val rel = path.removePrefix("/")
            if (".." in rel) return notFound()
            return asset("web/$rel", mime(rel))
        }
        val type = session.headers["content-type"]
        val body: ByteArray? = if (session.method == Method.POST) {
            val len = session.headers["content-length"]?.toIntOrNull() ?: 0
            if (len > MAX_BODY) return newFixedLengthResponse(Response.Status.BAD_REQUEST, "text/plain", "too large")
            ByteArray(len).also { buf -> var off = 0; while (off < len) { val n = session.inputStream.read(buf, off, len - off); if (n < 0) break; off += n } }
        } else null
        // Method, path and body size only (never the content): lets a device check see
        // that the page's recording arrived, in release builds too.
        if (body != null) android.util.Log.i("tablet", "request ${session.method} $path body=${body.size} bytes")
        val query = session.parameters.mapValues { it.value.firstOrNull() ?: "" }
        // One bad request must never take the whole app down.
        val r = try { api.handle(session.method.name, path, query, body, type) }
                catch (e: Exception) {
                    android.util.Log.e("tablet", "request failed: ${session.method} $path", e)
                    org.team8bitpool.app.core.Resp.error(500, "Internal error: ${e.javaClass.simpleName}")
                }
        val status = Response.Status.lookup(r.status) ?: Response.Status.INTERNAL_ERROR
        return newFixedLengthResponse(status, r.type, ByteArrayInputStream(r.body), r.body.size.toLong())
    }

    private fun asset(name: String, type: String): Response = try {
        val bytes = assets.open(name).use { it.readBytes() }
        newFixedLengthResponse(Response.Status.OK, type, ByteArrayInputStream(bytes), bytes.size.toLong())
    } catch (_: FileNotFoundException) { notFound() }

    private fun notFound() = newFixedLengthResponse(Response.Status.NOT_FOUND, "text/plain", "not found")

    private fun mime(name: String) = when (name.substringAfterLast('.').lowercase()) {
        "ttf" -> "font/ttf"; "woff2" -> "font/woff2"; "css" -> "text/css"; "js" -> "text/javascript"
        "png" -> "image/png"; "svg" -> "image/svg+xml"; else -> "application/octet-stream"
    }

    companion object {
        const val PORT = 5000
        private const val MAX_BODY = 32 * 1024 * 1024
    }
}
