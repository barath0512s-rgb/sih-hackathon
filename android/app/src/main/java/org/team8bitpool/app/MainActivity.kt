package org.team8bitpool.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import org.json.JSONObject
import org.team8bitpool.app.bridge.MicBridge
import org.team8bitpool.app.bridge.PackBridge
import org.team8bitpool.app.core.Api
import org.team8bitpool.app.core.Pack
import org.team8bitpool.app.core.Store
import org.team8bitpool.app.server.LocalServer
import java.io.File
import java.io.InputStream
import java.net.URL
import javax.net.ssl.HttpsURLConnection
import kotlin.concurrent.thread

/**
 * The tablet app: frontend.html in a WebView, talking to the in-app server on
 * 127.0.0.1:5000 exactly as a browser talks to the hub.
 */
class MainActivity : Activity() {
    private lateinit var web: WebView
    private var server: LocalServer? = null
    @Volatile private var pack: Pack? = null
    private val packRoot get() = File(filesDir, "packs")

    @SuppressLint("SetJavaScriptEnabled", "JavascriptInterface")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        pack = runCatching { File(packRoot, "current").takeIf { it.isDirectory }?.let { Pack(it) } }
            .onFailure { Log.e(TAG, "pack unreadable", it) }.getOrNull()
        val defaults = JSONObject(assets.open("app_config.json").use { it.readBytes().decodeToString() })
        val api = Api({ pack }, Store(File(filesDir, "store")), defaultConfig = defaults)
        server = LocalServer(assets, api).also { it.start(5000, false) }

        web = WebView(this)
        setContentView(web)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.mediaPlaybackRequiresUserGesture = false
        web.settings.allowFileAccess = false
        web.settings.allowContentAccess = false
        web.webViewClient = object : WebViewClient() {
            // Only the in-app server is ever shown; any other link stays out.
            override fun shouldOverrideUrlLoading(view: WebView, url: String) = !url.startsWith(ORIGIN)
        }
        web.webChromeClient = WebChromeClient()
        web.addJavascriptInterface(MicBridge(
            { checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED },
            { runOnUiThread { requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQ_MIC) } }), "VaaniMic")
        web.addJavascriptInterface(PackBridge(::pickPack, ::downloadPack, ::packStatus), "VaaniPack")
        debugImport(intent)
        web.loadUrl("$ORIGIN/")
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        debugImport(intent)
    }

    /**
     * Debug builds only, for tools/android/device_check.py: import a pack that
     * adb placed in the app's own files directory (run-as), through the same
     * verified import as the file picker.
     */
    private fun debugImport(intent: Intent?) {
        if (applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE == 0) return
        intent?.getIntExtra("mic_test_ms", 0)?.takeIf { it > 0 }?.let { micTest(it) }
        val name = intent?.getStringExtra("import_pack") ?: return
        val f = File(filesDir, name).canonicalFile
        if (f.parentFile != filesDir.canonicalFile || !f.isFile) return
        thread(name = "pack-import") {
            runCatching { f.inputStream().use { install(it) } }.onFailure { report(false, it.message ?: "import failed") }
            f.delete()
        }
    }

    /**
     * Debug builds only: record `ms` milliseconds through the same MicBridge the page
     * uses, and write what came out (bytes, RMS, peak) to files/mic_test.json for
     * tools/android/device_check.py.
     */
    private fun micTest(ms: Int) = thread(name = "mic-test") {
        val mic = MicBridge({ checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED }, {})
        val result = JSONObject()
        if (!mic.start()) {
            result.put("ok", false).put("error", "microphone not available or no permission")
        } else {
            Thread.sleep(ms.toLong())
            val wav = android.util.Base64.decode(mic.stop(), android.util.Base64.NO_WRAP)
            val pcm = java.nio.ByteBuffer.wrap(wav, 44, maxOf(0, wav.size - 44)).order(java.nio.ByteOrder.LITTLE_ENDIAN).asShortBuffer()
            var sum = 0.0; var peak = 0
            for (i in 0 until pcm.remaining()) { val v = pcm.get(i).toInt(); sum += v * v.toDouble(); peak = maxOf(peak, Math.abs(v)) }
            val n = pcm.remaining()
            result.put("ok", n > 0).put("wav_bytes", wav.size).put("samples", n).put("seconds", n / 16000.0)
                .put("rms", if (n > 0) Math.sqrt(sum / n) / 32768.0 else 0.0).put("peak", peak / 32768.0)
        }
        File(filesDir, "mic_test.json").writeText(result.toString())
        Log.i(TAG, "mic_test $result")
    }

    private fun packStatus(): JSONObject = pack?.manifest?.let {
        JSONObject().put("installed", true).put("created", it.optString("created")).put("counts", it.optJSONObject("counts"))
    } ?: JSONObject().put("installed", false)

    private fun pickPack() = runOnUiThread {
        startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
            .setType("*/*").putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("application/zip", "application/octet-stream")), REQ_PACK)
    }

    private fun downloadPack(url: String) {
        if (!url.startsWith("https://")) return report(false, "Use the hub's https:// address")
        thread(name = "pack-download") {
            runCatching {
                val c = URL(url.trimEnd('/') + "/pack/latest").openConnection() as HttpsURLConnection
                c.connectTimeout = 10_000; c.readTimeout = 60_000
                if (c.responseCode != 200) error("hub answered ${c.responseCode}")
                c.inputStream.use { install(it) }
            }.onFailure { report(false, it.message ?: "download failed") }
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        val uri = data?.data
        if (requestCode != REQ_PACK || resultCode != RESULT_OK || uri == null) return
        thread(name = "pack-import") {
            runCatching { contentResolver.openInputStream(uri)!!.use { install(it) } }
                .onFailure { report(false, it.message ?: "import failed") }
        }
    }

    private fun install(s: InputStream) {
        val p = Pack.import(s, packRoot)
        pack = p
        report(true, "Content pack installed", p.manifest.optJSONObject("counts"))
    }

    private fun report(ok: Boolean, message: String, counts: JSONObject? = null) = runOnUiThread {
        val arg = JSONObject().put("ok", ok).put("message", message).put("counts", counts ?: JSONObject.NULL)
        web.evaluateJavascript("window.onPackImported && window.onPackImported($arg)", null)
    }

    override fun onDestroy() {
        server?.stop()
        super.onDestroy()
    }

    companion object {
        private const val TAG = "tablet"
        const val ORIGIN = "http://127.0.0.1:5000"
        private const val REQ_MIC = 1
        private const val REQ_PACK = 2
    }
}
